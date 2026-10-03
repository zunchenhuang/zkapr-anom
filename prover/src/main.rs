// Groth16 (BN254, arkworks) over Circom .r1cs/.wtns: circuit-specific setup, prove, verify.
use ark_bn254::{Bn254, Fr};
use ark_ff::PrimeField;
use ark_groth16::{Groth16, Proof, ProvingKey, VerifyingKey, prepare_verifying_key};
use ark_relations::lc;
use ark_relations::r1cs::{ConstraintMatrices, ConstraintSynthesizer, ConstraintSystemRef, LinearCombination, SynthesisError, Variable};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use ark_snark::SNARK;
mod crs;
use std::fs;
use std::time::Instant;
use ark_std::UniformRand;

struct R1cs { n_wires: usize, n_pub: usize, cons: Vec<[Vec<(usize, Fr)>; 3]> }

fn u32le(b: &[u8], o: usize) -> u32 { u32::from_le_bytes(b[o..o + 4].try_into().unwrap()) }
fn u64le(b: &[u8], o: usize) -> u64 { u64::from_le_bytes(b[o..o + 8].try_into().unwrap()) }

fn read_r1cs(path: &str) -> R1cs {
    let b = fs::read(path).unwrap();
    assert!(&b[0..4] == b"r1cs");
    let nsec = u32le(&b, 8) as usize;
    let mut o = 12;
    let (mut fs_, mut n_wires, mut n_pub, mut m) = (32usize, 0usize, 0usize, 0usize);
    let mut cons_off = 0;
    for _ in 0..nsec {
        let t = u32le(&b, o); let sz = u64le(&b, o + 4) as usize; let s = o + 12;
        if t == 1 {
            fs_ = u32le(&b, s) as usize;
            let p = s + 4 + fs_;
            n_wires = u32le(&b, p) as usize;
            n_pub = (u32le(&b, p + 4) + u32le(&b, p + 8)) as usize;
            m = u32le(&b, p + 24) as usize;
        } else if t == 2 { cons_off = s; }
        o = s + sz;
    }
    let mut cons = Vec::with_capacity(m);
    let mut p = cons_off;
    for _ in 0..m {
        let mut abc: [Vec<(usize, Fr)>; 3] = [vec![], vec![], vec![]];
        for k in 0..3 {
            let nnz = u32le(&b, p) as usize; p += 4;
            for _ in 0..nnz {
                let w = u32le(&b, p) as usize; p += 4;
                let c = Fr::from_le_bytes_mod_order(&b[p..p + fs_]); p += fs_;
                abc[k].push((w, c));
            }
        }
        cons.push(abc);
    }
    R1cs { n_wires, n_pub, cons }
}

fn read_wtns(path: &str) -> Vec<Fr> {
    let b = fs::read(path).unwrap();
    assert!(&b[0..4] == b"wtns");
    let nsec = u32le(&b, 8) as usize;
    let mut o = 12; let mut fs_ = 32; let mut n = 0; let mut vals = vec![];
    for _ in 0..nsec {
        let t = u32le(&b, o); let sz = u64le(&b, o + 4) as usize; let s = o + 12;
        if t == 1 { fs_ = u32le(&b, s) as usize; n = u32le(&b, s + 4 + fs_) as usize; }
        if t == 2 { for i in 0..n { vals.push(Fr::from_le_bytes_mod_order(&b[s + i * fs_..s + (i + 1) * fs_])); } }
        o = s + sz;
    }
    vals
}

struct Circ<'a> { r: &'a R1cs, w: Option<&'a Vec<Fr>> }

impl<'a> ConstraintSynthesizer<Fr> for Circ<'a> {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        let mut vars = Vec::with_capacity(self.r.n_wires);
        vars.push(Variable::One);
        for i in 1..self.r.n_wires {
            let val = || self.w.map(|w| w[i]).ok_or(SynthesisError::AssignmentMissing);
            vars.push(if i <= self.r.n_pub { cs.new_input_variable(val)? } else { cs.new_witness_variable(val)? });
        }
        for c in &self.r.cons {
            let mk = |t: &Vec<(usize, Fr)>| { let mut l = lc!(); for (w, k) in t { l = l + (*k, vars[*w]); } l };
            let (a, b, cc): (LinearCombination<Fr>, _, _) = (mk(&c[0]), mk(&c[1]), mk(&c[2]));
            cs.enforce_constraint(a, b, cc)?;
        }
        Ok(())
    }
}

fn to_mats(r: R1cs) -> crs::Matrices {
    let (n_wires, n_inst) = (r.n_wires, 1 + r.n_pub);
    let (mut a, mut b, mut c) = (Vec::with_capacity(r.cons.len()), Vec::with_capacity(r.cons.len()), Vec::with_capacity(r.cons.len()));
    for [x, y, z] in r.cons.into_iter() { a.push(x); b.push(y); c.push(z); }
    crs::Matrices { n_wires, n_inst, a, b, c }
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let mut rng = rand::thread_rng();
    match a[1].as_str() {
        "setup" => {  // setup <r1cs> <pk> <vk>
            let r = read_r1cs(&a[2]);
            let t = Instant::now();
            let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(Circ { r: &r, w: None }, &mut rng).unwrap();
            let dt = t.elapsed().as_secs_f64();
            let mut f = vec![]; pk.serialize_compressed(&mut f).unwrap(); fs::write(&a[3], &f).unwrap();
            let mut g = vec![]; vk.serialize_compressed(&mut g).unwrap(); fs::write(&a[4], &g).unwrap();
            println!("{{\"t_setup\":{},\"pk_bytes\":{},\"vk_bytes\":{},\"constraints\":{},\"wires\":{}}}", dt, f.len(), g.len(), r.cons.len(), r.n_wires);
        }
        "prove" => {  // prove <r1cs> <wtns> <pk> <proof> <public>
            let r = read_r1cs(&a[2]); let w = read_wtns(&a[3]);
            assert_eq!(w.len(), r.n_wires, "witness/wire count mismatch");
            let pk = ProvingKey::<Bn254>::deserialize_compressed_unchecked(&fs::read(&a[4]).unwrap()[..]).unwrap();
            let t = Instant::now();
            let pr = Groth16::<Bn254>::prove(&pk, Circ { r: &r, w: Some(&w) }, &mut rng).unwrap();
            let dt = t.elapsed().as_secs_f64();
            let mut f = vec![]; pr.serialize_compressed(&mut f).unwrap(); fs::write(&a[5], &f).unwrap();
            let mut g = vec![]; for i in 1..=r.n_pub { w[i].serialize_compressed(&mut g).unwrap(); } fs::write(&a[6], &g).unwrap();
            println!("{{\"t_prove\":{},\"proof_bytes\":{}}}", dt, f.len());
        }
        "setup2" => {  // setup2 <r1cs> <pk> <vk> <aux>: customer setup with a verifiable CRS
            let r = read_r1cs(&a[2]); let m = to_mats(r);
            let t = Instant::now();
            let (pk, vk, aux) = crs::setup(&m, &mut rng);
            let dt = t.elapsed().as_secs_f64();
            let mut f = vec![]; pk.serialize_compressed(&mut f).unwrap(); fs::write(&a[3], &f).unwrap();
            let mut g = vec![]; vk.serialize_compressed(&mut g).unwrap(); fs::write(&a[4], &g).unwrap();
            let mut h = vec![]; aux.serialize_compressed(&mut h).unwrap(); fs::write(&a[5], &h).unwrap();
            println!("{{\"t_setup\":{},\"pk_bytes\":{},\"vk_bytes\":{},\"aux_bytes\":{},\"constraints\":{},\"wires\":{}}}", dt, f.len(), g.len(), h.len(), m.a.len(), m.n_wires);
        }
        "crscheck" => {  // crscheck <r1cs> <pk> <aux>: vendor verifies the CRS before proving
            let r = read_r1cs(&a[2]); let m = to_mats(r);
            let t = Instant::now();
            // Compressed decoding already yields points on the curve. BN254 G1 has cofactor 1, so only
            // G2 points need an explicit subgroup check (done in crs::validate).
            let pk = ProvingKey::<Bn254>::deserialize_compressed_unchecked(&fs::read(&a[3]).unwrap()[..]);
            let aux = crs::Aux::deserialize_compressed_unchecked(&fs::read(&a[4]).unwrap()[..]);
            let res = match (pk, aux) {
                (Ok(pk), Ok(aux)) => crs::check(&m, &pk, &aux, &mut rng).and_then(|_| crs::validate(&pk, &aux)),
                _ => Err("deserialization (not on curve)".into()) };
            let dt = t.elapsed().as_secs_f64();
            match res { Ok(()) => println!("{{\"crs_ok\":true,\"t_crscheck\":{}}}", dt),
                        Err(e) => println!("{{\"crs_ok\":false,\"reason\":\"{}\",\"t_crscheck\":{}}}", e, dt) }
        }
        "subvert" => {  // subvert <mode> <pk> <aux> <out_pk> <out_aux>
            let mut pk = ProvingKey::<Bn254>::deserialize_compressed_unchecked(&fs::read(&a[3]).unwrap()[..]).unwrap();
            let mut aux = crs::Aux::deserialize_compressed_unchecked(&fs::read(&a[4]).unwrap()[..]).unwrap();
            crs::subvert(&a[2], &mut pk, &mut aux, &mut rng);
            let mut f = vec![]; pk.serialize_compressed(&mut f).unwrap(); fs::write(&a[5], &f).unwrap();
            let mut h = vec![]; aux.serialize_compressed(&mut h).unwrap(); fs::write(&a[6], &h).unwrap();
            println!("{{\"subverted\":\"{}\"}}", a[2]);
        }
        "prove2" => {  // memory-lean: prove directly from sparse matrices (no constraint system)
            let r1 = read_r1cs(&a[2]); let w = read_wtns(&a[3]);
            assert_eq!(w.len(), r1.n_wires, "witness/wire count mismatch");
            let (n_pub, n_wires, m) = (r1.n_pub, r1.n_wires, r1.cons.len());
            let mut mats: [Vec<Vec<(Fr, usize)>>; 3] = [Vec::with_capacity(m), Vec::with_capacity(m), Vec::with_capacity(m)];
            let mut nnz = [0usize; 3];
            for c in r1.cons.into_iter() {
                for (k, t) in c.into_iter().enumerate() {
                    nnz[k] += t.len();
                    mats[k].push(t.into_iter().map(|(wi, co)| (co, wi)).collect());
                }
            }
            let [ma, mb, mc] = mats;
            let cm = ConstraintMatrices { num_instance_variables: 1 + n_pub, num_witness_variables: n_wires - 1 - n_pub,
                num_constraints: m, a_num_non_zero: nnz[0], b_num_non_zero: nnz[1], c_num_non_zero: nnz[2], a: ma, b: mb, c: mc };
            let pk = ProvingKey::<Bn254>::deserialize_compressed_unchecked(&fs::read(&a[4]).unwrap()[..]).unwrap();
            let t = Instant::now();
            let (rr, ss) = (Fr::rand(&mut rng), Fr::rand(&mut rng));
            let pr = Groth16::<Bn254>::create_proof_with_reduction_and_matrices(&pk, rr, ss, &cm, 1 + n_pub, m, &w).unwrap();
            let dt = t.elapsed().as_secs_f64();
            let mut f = vec![]; pr.serialize_compressed(&mut f).unwrap(); fs::write(&a[5], &f).unwrap();
            let mut g = vec![]; for i in 1..=n_pub { w[i].serialize_compressed(&mut g).unwrap(); } fs::write(&a[6], &g).unwrap();
            println!("{{\"t_prove\":{},\"proof_bytes\":{}}}", dt, f.len());
        }
        "verify" => {  // verify <vk> <proof> <public>
            let vk = VerifyingKey::<Bn254>::deserialize_compressed(&fs::read(&a[2]).unwrap()[..]).unwrap();
            let pb = fs::read(&a[3]).unwrap();
            let pub_b = fs::read(&a[4]).unwrap();
            let mut pubs = vec![]; let mut s = &pub_b[..];
            while !s.is_empty() { pubs.push(Fr::deserialize_compressed(&mut s).unwrap()); }
            let t0 = Instant::now();
            let ok = match Proof::<Bn254>::deserialize_compressed(&pb[..]) {
                Ok(pr) => { let pvk = prepare_verifying_key(&vk); Groth16::<Bn254>::verify_with_processed_vk(&pvk, &pubs, &pr).unwrap_or(false) }
                Err(_) => false };
            let t_full = t0.elapsed().as_secs_f64() * 1e3;
            let n = 20; let t = Instant::now();
            if let Ok(pr) = Proof::<Bn254>::deserialize_compressed(&pb[..]) {
                for _ in 0..n { let pvk = prepare_verifying_key(&vk); let _ = Groth16::<Bn254>::verify_with_processed_vk(&pvk, &pubs, &pr); } }
            println!("{{\"ok\":{},\"t_verify_ms\":{},\"t_verify_first_ms\":{}}}", ok, t.elapsed().as_secs_f64() * 1e3 / n as f64, t_full);
        }
        _ => panic!("usage"),
    }
}
