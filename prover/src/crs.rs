//! Verifiable Groth16 CRS (customer setup) and vendor-side CRS well-formedness check.
//! The CRS is the standard Groth16 key plus auxiliary elements
//! P^{tau^k} (k < n), Q, Q^tau, Q^{tau^n}, Q^alpha, which let the vendor check that every
//! element is consistent with one nonzero trapdoor (alpha, beta, gamma, delta, tau),
//! following Fuchsbauer (PKC 2018). Pairing equations are batched with private randomness.
use ark_bn254::{Bn254, Fr, G1Affine, G1Projective as G1, G2Affine, G2Projective as G2};
use ark_ec::{pairing::Pairing, scalar_mul::fixed_base::FixedBase, AffineRepr, CurveGroup, Group, VariableBaseMSM};
use ark_ff::{Field, One, PrimeField, UniformRand, Zero};
use ark_groth16::{ProvingKey, VerifyingKey};
use ark_poly::{EvaluationDomain, GeneralEvaluationDomain};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};

pub struct Matrices { pub n_wires: usize, pub n_inst: usize, pub a: Vec<Vec<(usize, Fr)>>, pub b: Vec<Vec<(usize, Fr)>>, pub c: Vec<Vec<(usize, Fr)>> }

#[derive(CanonicalSerialize, CanonicalDeserialize)]
pub struct Aux { pub powers: Vec<G1Affine>, pub q: G2Affine, pub q_tau: G2Affine, pub q_tau_n: G2Affine, pub q_alpha: G2Affine }

fn domain(m: &Matrices) -> GeneralEvaluationDomain<Fr> {
    GeneralEvaluationDomain::<Fr>::new(m.a.len() + m.n_inst).expect("domain")
}

/// Evaluations of the QAP column polynomials at tau, exactly as LibsnarkReduction.
fn qap_eval(m: &Matrices, u: &[Fr]) -> (Vec<Fr>, Vec<Fr>, Vec<Fr>) {
    let (mut a, mut b, mut c) = (vec![Fr::zero(); m.n_wires], vec![Fr::zero(); m.n_wires], vec![Fr::zero(); m.n_wires]);
    let nc = m.a.len();
    for i in 0..m.n_inst { a[i] = u[nc + i]; }
    for j in 0..nc {
        for (w, k) in &m.a[j] { a[*w] += u[j] * k; }
        for (w, k) in &m.b[j] { b[*w] += u[j] * k; }
        for (w, k) in &m.c[j] { c[*w] += u[j] * k; }
    }
    (a, b, c)
}

fn nz(rng: &mut impl rand::Rng) -> Fr { loop { let x = Fr::rand(rng); if !x.is_zero() { return x; } } }

pub fn setup(m: &Matrices, rng: &mut impl rand::Rng) -> (ProvingKey<Bn254>, VerifyingKey<Bn254>, Aux) {
    let d = domain(m); let n = d.size();
    let tau = d.sample_element_outside_domain(rng);
    let (alpha, beta, gamma, delta) = (nz(rng), nz(rng), nz(rng), nz(rng));
    let u = d.evaluate_all_lagrange_coefficients(tau);
    let zt = d.evaluate_vanishing_polynomial(tau);
    let (a, b, c) = qap_eval(m, &u);
    let (gi, di) = (gamma.inverse().unwrap(), delta.inverse().unwrap());
    let ni = m.n_inst;
    let gabc: Vec<Fr> = (0..ni).map(|i| (beta * a[i] + alpha * b[i] + c[i]) * gi).collect();
    let l: Vec<Fr> = (ni..m.n_wires).map(|i| (beta * a[i] + alpha * b[i] + c[i]) * di).collect();
    let mut pw = Vec::with_capacity(n); let mut t = Fr::one();
    for _ in 0..n { pw.push(t); t *= tau; }
    let h: Vec<Fr> = (0..n - 1).map(|i| zt * di * pw[i]).collect();
    let (p, q) = (G1::generator(), G2::generator());
    let bits = Fr::MODULUS_BIT_SIZE as usize;
    let w1 = FixedBase::get_mul_window_size(4 * m.n_wires + 2 * n);
    let t1 = FixedBase::get_window_table::<G1>(bits, w1, p);
    let w2 = FixedBase::get_mul_window_size(m.n_wires);
    let t2 = FixedBase::get_window_table::<G2>(bits, w2, q);
    let g1 = |s: &[Fr]| G1::normalize_batch(&FixedBase::msm::<G1>(bits, w1, &t1, s));
    let vk = VerifyingKey::<Bn254> {
        alpha_g1: (p * alpha).into_affine(), beta_g2: (q * beta).into_affine(),
        gamma_g2: (q * gamma).into_affine(), delta_g2: (q * delta).into_affine(), gamma_abc_g1: g1(&gabc) };
    let pk = ProvingKey::<Bn254> {
        vk: vk.clone(), beta_g1: (p * beta).into_affine(), delta_g1: (p * delta).into_affine(),
        a_query: g1(&a), b_g1_query: g1(&b),
        b_g2_query: G2::normalize_batch(&FixedBase::msm::<G2>(bits, w2, &t2, &b)),
        h_query: g1(&h), l_query: g1(&l) };
    let tn = tau.pow([n as u64]);
    let aux = Aux { powers: g1(&pw), q: q.into_affine(), q_tau: (q * tau).into_affine(),
                    q_tau_n: (q * tn).into_affine(), q_alpha: (q * alpha).into_affine() };
    (pk, vk, aux)
}

fn rv(n: usize, rng: &mut impl rand::Rng) -> Vec<Fr> { (0..n).map(|_| Fr::rand(rng)).collect() }
fn msm1(b: &[G1Affine], s: &[Fr]) -> G1 { G1::msm(&b[..s.len()], s).unwrap() }
fn msm2(b: &[G2Affine], s: &[Fr]) -> G2 { G2::msm(&b[..s.len()], s).unwrap() }
fn e(pairs: &[(G1, G2)]) -> ark_ec::pairing::PairingOutput<Bn254> {
    Bn254::multi_pairing(pairs.iter().map(|x| x.0.into_affine()), pairs.iter().map(|x| x.1.into_affine()))
}

/// Combined column polynomial sum_i r_i * col_i(X) in coefficient form, for wires in [lo, hi).
fn combo_coeffs(m: &Matrices, d: &GeneralEvaluationDomain<Fr>, which: char, r: &[Fr], lo: usize) -> Vec<Fr> {
    let nc = m.a.len();
    let mut s = vec![Fr::zero(); d.size()];
    let mat = match which { 'a' => &m.a, 'b' => &m.b, _ => &m.c };
    let hi = lo + r.len();
    if which == 'a' { for i in lo.max(0)..hi.min(m.n_inst) { s[nc + i] += r[i - lo]; } }
    for j in 0..nc { for (w, k) in &mat[j] { if *w >= lo && *w < hi { s[j] += r[*w - lo] * k; } } }
    d.ifft(&s)
}

/// Vendor-side check. Returns Err(reason) on the first failed condition.
pub fn check(m: &Matrices, pk: &ProvingKey<Bn254>, aux: &Aux, rng: &mut impl rand::Rng) -> Result<(), String> {
    let d = domain(m); let n = d.size(); let (nw, ni) = (m.n_wires, m.n_inst);
    let vk = &pk.vk;
    // shapes
    if aux.powers.len() != n || pk.a_query.len() != nw || pk.b_g1_query.len() != nw || pk.b_g2_query.len() != nw
        || pk.l_query.len() != nw - ni || vk.gamma_abc_g1.len() != ni || pk.h_query.len() != n - 1 { return Err("shape".into()); }
    let (p, q) = (aux.powers[0].into_group(), aux.q.into_group());
    // non-degeneracy: P, Q, P^tau, alpha, beta, gamma, delta nonzero
    for (name, z) in [("P", p.is_zero()), ("Q", q.is_zero()), ("P^tau", aux.powers[1].is_zero()),
                      ("alpha", vk.alpha_g1.is_zero()), ("beta", pk.beta_g1.is_zero()), ("delta", pk.delta_g1.is_zero()),
                      ("gamma", vk.gamma_g2.is_zero()), ("Q^alpha", aux.q_alpha.is_zero())] {
        if z { return Err(format!("degenerate {}", name)); }
    }
    // 1. powers of tau are consistent: P^{tau^{k+1}} = (P^{tau^k})^tau
    let r = rv(n - 1, rng);
    if e(&[(msm1(&aux.powers, &r), aux.q_tau.into_group())]) != e(&[(msm1(&aux.powers[1..], &r), q)]) { return Err("powers".into()); }
    // 2. Q^{tau^n}
    if e(&[(aux.powers[n - 1].into_group(), aux.q_tau.into_group())]) != e(&[(p, aux.q_tau_n.into_group())]) { return Err("Q^tau^n".into()); }
    // 3. same alpha, beta, delta in G1 and G2
    if e(&[(vk.alpha_g1.into_group(), q)]) != e(&[(p, aux.q_alpha.into_group())]) { return Err("alpha".into()); }
    if e(&[(pk.beta_g1.into_group(), q)]) != e(&[(p, vk.beta_g2.into_group())]) { return Err("beta".into()); }
    if e(&[(pk.delta_g1.into_group(), q)]) != e(&[(p, vk.delta_g2.into_group())]) { return Err("delta".into()); }
    // 4. A and B(G1) queries are the QAP columns evaluated at tau
    for (which, query) in [('a', &pk.a_query), ('b', &pk.b_g1_query)] {
        let r = rv(nw, rng);
        if msm1(query, &r) != msm1(&aux.powers, &combo_coeffs(m, &d, which, &r, 0)) { return Err(format!("{}_query", which)); }
    }
    // 5. B in G2 matches B in G1
    let r = rv(nw, rng);
    if e(&[(msm1(&pk.b_g1_query, &r), q)]) != e(&[(p, msm2(&pk.b_g2_query, &r))]) { return Err("b_g2_query".into()); }
    // 6. L (witness wires, under delta) and gamma_abc (instance wires, under gamma)
    for (lo, hi, query, key) in [(ni, nw, &pk.l_query, vk.delta_g2), (0, ni, &vk.gamma_abc_g1, vk.gamma_g2)] {
        let r = rv(hi - lo, rng);
        let lhs = e(&[(msm1(query, &r), key.into_group())]);
        let ca = msm1(&pk.a_query[lo..hi], &r);
        let cb = msm1(&pk.b_g1_query[lo..hi], &r);
        let cc = msm1(&aux.powers, &combo_coeffs(m, &d, 'c', &r, lo));
        if lhs != e(&[(ca, vk.beta_g2.into_group()), (cb, aux.q_alpha.into_group()), (cc, q)]) {
            return Err(if lo == 0 { "gamma_abc".into() } else { "l_query".into() });
        }
    }
    // 7. H: h_i = P^{tau^i (tau^n - 1)/delta}
    let r = rv(n - 1, rng);
    if e(&[(msm1(&pk.h_query, &r), vk.delta_g2.into_group())]) != e(&[(msm1(&aux.powers, &r), aux.q_tau_n.into_group() - q)]) {
        return Err("h_query".into());
    }
    Ok(())
}

/// Customer-side subversions used in the evaluation (each must be rejected by `check`).
pub fn subvert(mode: &str, pk: &mut ProvingKey<Bn254>, aux: &mut Aux, rng: &mut impl rand::Rng) {
    let rnd1 = || G1::rand(&mut rand::thread_rng()).into_affine();
    match mode {
        "h" => { let i = pk.h_query.len() / 2; pk.h_query[i] = rnd1(); }
        "l" => { let i = pk.l_query.len() / 3; pk.l_query[i] = (pk.l_query[i].into_group() * Fr::from(2u64)).into_affine(); }
        "alpha" => { pk.vk.alpha_g1 = (pk.vk.alpha_g1.into_group() * nz(rng)).into_affine(); }
        "gamma0" => { pk.vk.gamma_g2 = G2Affine::zero(); for g in pk.vk.gamma_abc_g1.iter_mut() { *g = G1Affine::zero(); } }
        "a" => { let i = pk.a_query.len() / 2; pk.a_query[i] = (pk.a_query[i].into_group() + aux.powers[0].into_group()).into_affine(); }
        _ => panic!("unknown subversion"),
    }
}

/// Subgroup membership for every G2 element (G1 on BN254 has cofactor 1).
pub fn validate(pk: &ProvingKey<Bn254>, aux: &Aux) -> Result<(), String> {
    let vk = &pk.vk;
    let mut g2: Vec<&G2Affine> = vec![&vk.beta_g2, &vk.gamma_g2, &vk.delta_g2, &aux.q, &aux.q_tau, &aux.q_tau_n, &aux.q_alpha];
    g2.extend(pk.b_g2_query.iter());
    for x in g2 { if !(x.is_on_curve() && x.is_in_correct_subgroup_assuming_on_curve()) { return Err("G2 point not in subgroup".into()); } }
    Ok(())
}
