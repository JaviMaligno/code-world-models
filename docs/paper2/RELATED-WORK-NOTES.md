# Related work: verified references and how paper 2 relates (review point #21)

Companion to `docs/paper2/RELATED-WORK-REFS.bib`. **59 entries, all verified; 3 candidates
dropped for lack of verification** (listed at the end). Nothing here has been written into
`main.tex` or `references.bib` — both are owned by other tasks.

## How verification was done

Every entry was checked against a machine-readable authority, not against memory and not
against a search-result snippet:

* **Crossref REST API** (`https://api.crossref.org/works/{DOI}` for the exact record;
  `?query.bibliographic=` for discovery). Title, full author list, container title,
  volume/issue/pages, and `published-print` vs `published-online` dates were read off the
  returned JSON.
* **arXiv API** (`http://export.arxiv.org/api/query`) for preprint ids, author lists and
  `journal_ref`.
* **Official proceedings pages** where the venue has no DOI: `proceedings.mlr.press/v54`,
  `/v125`, `/v155` (PMLR), `papers.nips.cc` / `proceedings.neurips.cc`,
  `www2.eecs.berkeley.edu/Pubs/TechRpts`.
* **Open Library** (`openlibrary.org/search.json`) for the one book with no DOI.

Three of my initial attributions were **wrong and were corrected by verification** — worth
recording because they are exactly the failure mode this task exists to prevent:

| I believed | Authority says | Entry |
|---|---|---|
| Neural Predictive Monitoring includes R. Grosu | Bortolussi, Cairoli, Paoletti, **Smolka, Stoller** | `bortolussi2019npm` |
| Hybrid-automata mining includes G. Fainekos | Medhat, Ramesh, Bonakdarpour, **Fischmeister** | `medhat2015mining` |
| Simulation-guided Lyapunov includes K. Butts | Kapinski, Deshmukh, Sankaranarayanan, **Arechiga** | `kapinski2014simulation` |

Crossref's own record for `bemporad2005boundederror` misspells the first author as
"A. Bempora"; the bib uses the correct **Bemporad**, confirmed against the other three
Bemporad entries and the IEEE TAC record.

**Mechanical check.** The file was compiled through `pdflatex` + `bibtex` with
`plainnat` (the paper's style) citing all 59 keys: `bibtex` reports
`You've used 59 entries` with **zero `warning$` calls**, the `.bbl` contains 59
`\bibitem`s, and LaTeX reports no undefined citations. It also has **zero key collisions**
with the 21 keys already in `references.bib`.

## Overlaps with the existing `references.bib` — do NOT duplicate these

The following topics are already partly covered by keys in `references.bib`. New entries
here are additions to, not replacements for, them:

| Topic | Already in `references.bib` |
|---|---|
| 3 (hybrid / PWA id) | `paoletti2007hybrid`, `bemporad1999control` |
| 4 (falsification, CPS testing) | `annpureddy2011staliro`, `corso2021survey` |
| 5 (runtime assurance, robust MPC) | `alshiekh2018shielding`, `rawlings2017mpc` |
| 6 (contact-rich sysid) | `fazeli2017contact` |
| 7 (learned continuous dynamics) | `nagabandi2018neural`, `chua2018deep` |
| 10 (property-based testing, rare events) | `claessen2000quickcheck`, `rubinstein2017montecarlo` |
| 11 (objective mismatch, model exploitation) | `lambert2020objective`, `janner2019mbpo`, `hafner2020dreamer` |

`bemporad2005boundederror` shares a first author with `bemporad1999control` but is a
different work (bounded-error PWA identification vs MLD modelling); `fazeli2020limitations`
shares authors with `fazeli2017contact` but is the negative-result companion.

---

## 1. CEGIS / counterexample-guided inductive synthesis — the direct analogue

**What the literature establishes.** CEGIS (Solar-Lezama et al., ASPLOS 2006; formalised
in the Sketch thesis) is a two-player loop: a *learner* proposes a candidate program
consistent with a finite set of counterexamples, a *verifier* either certifies the
candidate against a specification or returns a new counterexample, and the loop repeats.
Its guarantee is entirely inherited from the verifier: **when the verifier is complete
relative to the specification, CEGIS terminates only on a program that provably satisfies
the specification on the whole input domain**, and each iteration strictly shrinks the
candidate space. Jha and Seshia (Acta Informatica 2017) make the dependence explicit by
building a theory of *oracle-guided* inductive synthesis in which what you can synthesise
is a function of which oracles you have — counterexample, membership, equivalence,
witness — and Angluin's classical result (topic 12) is the same statement one field over.
SyGuS (Alur et al., FMCAD 2013) standardised the format; the programming-by-example line
(Gulwani, POPL 2011; Gulwani–Polozov–Singh 2017) is the same loop *without* a verifier,
where generalisation beyond the examples is supplied by a ranking function or a
domain-specific bias — explicitly a heuristic, never a guarantee.

**How paper 2 relates — the unflattering version.** The paper's synthesize-gate-refine
pipeline *is* a CEGIS loop. The LLM is the learner; the gate's failing transitions are the
counterexamples; the refine iteration is the CEGIS iteration. The one substitution the
paper makes is the load-bearing one: **its counterexample oracle is uniform random
sampling of transitions, not a verifier.** A CEGIS verifier is complete relative to a
specification, so "no counterexample" means *there is none*. A sampling gate is not
complete relative to anything: "no counterexample" means *none was drawn*, and the paper's
own $(1-r)^N$ is the exact probability of that mistake for a rule of rarity $r$. So the
paper's loop is not CEGIS-with-a-cheap-verifier; when the mode is absent from the sample it
is *programming by example*, and everything that then happens off-sample is decided by the
learner's prior — which is precisely what the paper measures (GPT-5.x's clamp prior
repairs; its region prior does not; Claude's symmetry prior invents a phantom mode).
**This is not news to the CEGIS literature, and the paper should say so.** Two lines
already know it. (i) The oracle-guided theory (`jha2017theory`) is built around the fact
that weaker oracles buy weaker conclusions, with PBE as the degenerate bottom case.
(ii) The literature that had to run CEGIS against physical dynamics, where no complete
verifier exists, replaced the verifier with *simulation* and was explicit that the result
is not a proof: `kapinski2014simulation` runs exactly a synthesize/simulate/refine loop for
Lyapunov candidates, and `ravanbakhsh2019clf` learns control Lyapunov functions from
counterexamples and demonstrations — both then work hard to *recover* a soundness claim
(bounded verifier, SMT check on the final candidate) rather than accept the sampling
verdict. `abate2018cegist` is the same instinct in the other direction: keep the verifier
complete by pushing it into a theory solver. The honest positioning is therefore: paper 2
contributes not the observation that a sampling oracle is incomplete, but *a closed-form
law for how incomplete it is on a localized-rule failure* ($(1-r)^N$), a proof that the
missed-mode event is unlearnable from the sample by any learner (Prop. ident), and the
measurement of what a planner does with the certified artifact. What paper 2 must **not**
claim is that its gate certifies in the CEGIS sense.

Verification evidence:

| Key | Evidence | Confirmed at |
|---|---|---|
| `solarlezama2006sketching` | DOI `10.1145/1168857.1168907` (ASPLOS XII proceedings record; the SIGPLAN Notices mirror is `10.1145/1168918.1168907`) | `api.crossref.org/works/10.1145/1168857.1168907` |
| `solarlezama2008thesis` | UCB/EECS-2008-177, "Ph.D. thesis", 19 Dec 2008 | `www2.eecs.berkeley.edu/Pubs/TechRpts/2008/EECS-2008-177.html` |
| `jha2010oracle` | DOI `10.1145/1806799.1806833`, ICSE 2010, pp. 215–224 | Crossref |
| `jha2017theory` | DOI `10.1007/s00236-017-0294-5`, Acta Informatica 54(7):693–726 | Crossref |
| `alur2013sygus` | DOI `10.1109/FMCAD.2013.6679385`, FMCAD 2013, pp. 1–8, 10 authors | Crossref |
| `gulwani2011flashfill` | DOI `10.1145/1926385.1926423`, POPL 2011, pp. 317–330 | Crossref |
| `gulwani2017synthesis` | DOI `10.1561/2500000010`, Found. Trends Program. Lang. 4(1–2):1–119 | Crossref |
| `abate2018cegist` | DOI `10.1007/978-3-319-96145-3_15`, CAV 2018, pp. 270–288 | Crossref |
| `kapinski2014simulation` | DOI `10.1145/2562059.2562139`, HSCC 2014, pp. 133–142 | Crossref |
| `ravanbakhsh2019clf` | DOI `10.1007/s10514-018-9791-9`, Auton. Robots 43(2):275–307, print Feb 2019 (online 2018-08-06) | Crossref |

*Caveat:* the Sketch thesis exists as two Berkeley report numbers with the same title and
date — UCB/EECS-2008-**176** (typed "Technical Report") and **177** (typed "Ph.D.
thesis"). Both pages were fetched; the bib cites 177.

## 2. Active system identification / experiment design for dynamical systems

**What the literature establishes.** Which parameters you can recover is a property of the
*input signal*, not only of the estimator: Mehra (1974) posed optimal input design for
parameter estimation as a formal problem, Gevers (2005) traces how identification-for-control
made experiment design load-bearing again (you should optimise the experiment for the
control objective, not for prediction error), and Ljung's textbook is the standard statement
of identifiability under a given excitation. Wagenmaker and Jamieson (COLT 2020) give the
modern learning-theoretic version: for linear dynamical systems, *actively chosen* inputs
achieve sample complexities that passive random excitation cannot.

**How paper 2 relates.** This is the literature that most directly implies paper 2's
prescription, and the paper currently does not cite it at all. Paper 2's gate is a
*passive, non-adaptive* experiment: uniform random rollouts, chosen without reference to
what the model still gets wrong or where the planner intends to go. Its identifiability
proposition is the identifiability statement of this literature specialised to a hybrid
mode and a code hypothesis class — the excitation never enters the mode's region, so no
estimator recovers the mode's rule. The difference is the object: this literature designs
inputs to reduce *parameter* variance in a fixed parametric family, where the failure is
graded (large error bars); paper 2's failure is discrete and all-or-nothing (a rule is
present or absent in the program), and its consequence is measured through a *planner*
rather than through an estimation-error norm. The paper's open follow-up — "active boundary
probing" in §Limitations — is exactly an experiment-design problem, and should be named as
such rather than as a novel idea.

| Key | Evidence | Confirmed at |
|---|---|---|
| `mehra1974optimal` | DOI `10.1109/TAC.1974.1100701`, IEEE TAC 19(6):753–768 | Crossref |
| `gevers2005identification` | DOI `10.3166/ejc.11.335-352`, Eur. J. Control 11(4–5):335–352 | Crossref (a CDC 2005 plenary abstract with DOI `10.1109/CDC.2005.1582109` also exists) |
| `ljung1999sysid` | ISBN `0-13-656695-2` / `9780136566953`, Prentice Hall PTR, 2nd ed. — **no DOI; book-level verification only** | `openlibrary.org/search.json` |
| `wagenmaker2020active` | arXiv `2002.00495`; PMLR v125:3487–3582 | arXiv API + `proceedings.mlr.press/v125/` |

## 3. Experiment design and identification for hybrid and piecewise-affine systems

**What the literature establishes.** Identifying a PWA/hybrid system is a joint
*classification-and-regression* problem: you must recover the partition of the state-input
space as well as the affine law in each region. The canonical solutions are clustering-based
(Ferrari-Trecate et al., Automatica 2003), mixed-integer (Roll–Bemporad–Ljung, Automatica
2004), bounded-error / set-membership (Bemporad et al., IEEE TAC 2005) and algebraic
(Vidal et al., CDC 2003). The formal-methods branch learns hybrid *automata* from traces
(Medhat et al., EMSOFT 2015; García Soto et al., HSCC 2021) — and, critically for paper 2,
one of these is explicitly *active*: `soto2019membership` synthesises linear hybrid automata
using **membership queries**, i.e. it asks the system about points it chooses.

**How paper 2 relates.** Paper 2 studies the case this literature assumes away. Every method
above needs data in each mode: the clustering methods cannot form a cluster for a region with
no samples, the MIP and bounded-error formulations partition only the observed data, and the
trace-mining tools infer only modes that appear in a trace. Paper 2's contribution is not a
better identification algorithm — it is the statement that when the sample contains no
transition in the mode's region, *the omission is undetectable by the gate at rate
$(1-r)^N$* and unlearnable from the sample by any method in this list; and then a
measurement of what the planner does with the resulting certified program. The
representational half of the paper (Prop. Lipschitz) is also a statement about this
literature's hypothesis classes: a smooth learner cannot express the exactly localized
disagreement that a hybrid boundary permits, which is why the paper insists on *code* as the
hypothesis class rather than PWA-with-fixed-mode-count. `soto2019membership` is the
closest thing to paper 2's prescribed fix already existing, and should be cited where the
paper proposes active boundary probing.

| Key | Evidence | Confirmed at |
|---|---|---|
| `ferraritrecate2003clustering` | DOI `10.1016/S0005-1098(02)00224-8`, Automatica 39(2):205–217 | Crossref |
| `roll2004identification` | DOI `10.1016/j.automatica.2003.08.006`, Automatica 40(1):37–50 | Crossref |
| `bemporad2005boundederror` | DOI `10.1109/TAC.2005.856667`, IEEE TAC 50(10):1567–1580 | Crossref (author "Bempora" is a Crossref typo) |
| `vidal2003algebraic` | DOI `10.1109/CDC.2003.1272554`, CDC 2003, vol. 1, pp. 167–172 | Crossref |
| `soto2019membership` | DOI `10.1007/978-3-030-25540-4_16`, CAV 2019, pp. 297–314 | Crossref |
| `soto2021synthesis` | DOI `10.1145/3447928.3456704`, HSCC 2021, pp. 1–11 | Crossref |
| `medhat2015mining` | DOI `10.1109/EMSOFT.2015.7318273`, EMSOFT 2015, pp. 177–186 | Crossref |

## 4. Falsification-guided model learning; CEGAR for hybrid systems

**What the literature establishes.** CEGAR (Clarke et al., CAV 2000) is the abstraction
counterpart of CEGIS: verify a coarse abstraction, and when the verifier returns a spurious
counterexample, refine the abstraction *at that counterexample*. It was carried to hybrid
systems by Clarke et al. (TACAS 2003) and Alur–Dang–Ivančić (TCS 2006). The
learning-facing branch closes the loop the other way: `dreossi2018cegda` uses falsified
counterexamples as *training data* to retrain a learned component (counterexample-guided
data augmentation), `dreossi2019verifai` packages falsification + retraining as a toolkit,
and `yamagata2021falsification` learns a falsifier itself with deep RL. Together with
`annpureddy2011staliro` and `corso2021survey` (already cited) the message is uniform:
**directed search finds the rare violating input that random sampling misses.**

**How paper 2 relates.** Paper 2's existing text already makes the right point — its gate is
the "passive dual" of falsification — but it under-uses the refinement half. Two sharper
connections should be added. (i) CEGAR's spurious-counterexample-driven refinement is the
structural template for the paper's *distrust-region* mitigation: the planner discovers that
the model's prediction was refuted at a point and locally refines its trust region there.
The difference is soundness bookkeeping: CEGAR refines an abstraction that is
over-approximate by construction, so refinement preserves the guarantee; the fence refines a
*trust set* around an artifact with no over-approximation guarantee, which is why the paper
can only report a measured collapse of the exploitation and, on the 2D boundary, a
$7/20$ lock-in. (ii) `dreossi2018cegda` is the closest existing instance of "use the
counterexample to fix the model" — and its counterexamples come from a falsifier, whereas
paper 2's come from the gate's own random draw. That contrast is the paper's thesis in one
sentence, and it is currently unmade.

| Key | Evidence | Confirmed at |
|---|---|---|
| `clarke2000cegar` | DOI `10.1007/10722167_15`, CAV 2000, pp. 154–169 (JACM 2003 version: `10.1145/876638.876643`) | Crossref |
| `clarke2003hybridcegar` | DOI `10.1007/3-540-36577-X_14`, TACAS 2003, pp. 192–207 | Crossref |
| `alur2006predicate` | DOI `10.1016/j.tcs.2005.11.026`, TCS 354(2):250–271 | Crossref |
| `dreossi2018cegda` | DOI `10.24963/ijcai.2018/286`, IJCAI 2018, pp. 2071–2078 | Crossref + DBLP |
| `dreossi2019verifai` | DOI `10.1007/978-3-030-25540-4_25`, CAV 2019, pp. 432–442 | Crossref |
| `yamagata2021falsification` | DOI `10.1109/TSE.2020.2969178`, IEEE TSE 47(12):2823–2840 | Crossref |

*Note:* `yamagata2021falsification` is the journal version; the FM 2018 conference version
(DOI `10.1007/978-3-319-95582-7_27`) has **Akazaki** as first author. Do not merge the two
author orders.

## 5. Runtime assurance / simplex architectures; adaptive and learning MPC

**What the literature establishes.** The Simplex architecture (Seto et al., ACC 1998; Sha,
IEEE Software 2001) is the canonical answer to "deploy an unverified controller safely":
run it alongside a verified conservative baseline plus a decision module that switches to
the baseline before the state can leave a provably recoverable set. Learning MPC
(`rosolia2018lmpc`) improves a controller across iterations while keeping recursive
feasibility; the survey `hewing2020learningmpc` catalogues how learned models enter MPC and
what remains guaranteed; the predictive safety filter (`wabersich2021safetyfilter`) is the
modern Simplex — a minimally-invasive projection of any proposed input onto the set of
inputs that keeps a *known* backup controller viable.

**How paper 2 relates.** Every guarantee in this family is anchored to something known
a priori: a verified baseline controller, a recoverable set, or a bounded model-error
description. Paper 2's failure is designed to be invisible to all three anchors — the model
error is *unbounded but measure-zero-adjacent*, localized in a region the gate certified as
error-free, so an error bound tuned to the off-mode residual does not cover it and a safety
filter built on the same wrong model inherits the same blind spot. The distrust-region fence
is the same *shape* as a safety filter (override the planner near refuted predictions) with
the anchor moved: it is built from deployment-time observed refutations rather than from an
a-priori safe set, which is why it is a mitigation with measured behaviour and not a
certificate — and why it fails at $7/20$ on the 2D boundary where its unsigned-distance
tie-break lets the planner be pinned. The paper's shielding citation
(`alshiekh2018shielding`) covers the automaton-specification version of this; Simplex and
the safety filter are the control-theoretic version and are the more exact comparison.

| Key | Evidence | Confirmed at |
|---|---|---|
| `seto1998simplex` | DOI `10.1109/ACC.1998.703255`, ACC 1998, pp. 3504–3508 vol. 6 | Crossref |
| `sha2001simplicity` | DOI `10.1109/MS.2001.936213`, IEEE Software 18(4):20–28 | Crossref |
| `rosolia2018lmpc` | DOI `10.1109/TAC.2017.2753460`, IEEE TAC 63(7):1883–1896 | Crossref |
| `hewing2020learningmpc` | DOI `10.1146/annurev-control-090419-075625`, Annu. Rev. Control Robot. Auton. Syst. 3:269–296 | Crossref |
| `wabersich2021safetyfilter` | DOI `10.1016/j.automatica.2021.109597`, Automatica 129:109597 | Crossref |

## 6. Contact-mode discovery and identification in contact-rich dynamics

**What the literature establishes.** Contact dynamics is the physical archetype of the
paper's hybrid instrument, and this literature's central finding is a *negative* one that
paper 2's PatchField2D result echoes. `pfrommer2021contactnets` shows that learning
contact dynamics with a smooth end-to-end network is the wrong parameterisation and that
building the complementarity structure into an implicit loss works far better;
`parmar2021stiff` argues the point directly — stiff contact makes the loss landscape
pathological for deep learners, a *fundamental* rather than tuning-level challenge;
`fazeli2020limitations` shows that even the standard analytic planar contact models are
limited in performance and interpretability when fit to real data, complementing
`fazeli2017contact` (already cited) on what is identifiable from contact data at all.

**How paper 2 relates.** This is the strongest external corroboration of the paper's
representational proposition, and the citation should be made in that direction rather than
as a politeness. Prop. Lipschitz says an exactly localized disagreement forces unbounded
local Lipschitz structure; `parmar2021stiff` reports the empirical shadow of the same fact
(stiffness is what breaks smooth learners at contact), and `pfrommer2021contactnets` reports
the fix that is structurally the same as paper 2's — put the discontinuity in the
*hypothesis class* rather than hoping the fit finds it. The difference is what is being
learned: this literature learns contact *parameters and forces* given that contact happens
in the data, and its failures are accuracy failures; paper 2's failure is that the mode is
absent from the data and the resulting artifact is *certified*. Paper 2's PatchField2D
negative (0/156 region-rule repairs) is the code-hypothesis-class analogue of the
smooth-learner negatives here — and both stop short of contact-rich manipulation, which
paper 2 correctly lists as future work.

| Key | Evidence | Confirmed at |
|---|---|---|
| `pfrommer2021contactnets` | arXiv `2009.11193`; PMLR v155:2279–2291 (CoRL 2020, proceedings published 2021) | arXiv API + `proceedings.mlr.press/v155/` |
| `parmar2021stiff` | DOI `10.1109/IROS51168.2021.9636383`, IROS 2021, pp. 5181–5188 | Crossref |
| `fazeli2020limitations` | DOI `10.1007/978-3-030-28619-4_41`, *Robotics Research* (Springer Proc. Advanced Robotics), pp. 555–571, print 2020 | Crossref |

*Caveat:* for `fazeli2020limitations` the container title Crossref returns is
`Robotics Research` (the ISRR proceedings series volume). The bib records exactly that;
I did **not** verify which ISRR edition it is, so no symposium number is claimed.

## 7. Neural hybrid / switched dynamics models; mixture-of-experts dynamics

**What the literature establishes.** There is a mature family of hypothesis classes that
*can* represent mode structure: mixtures of experts with a learned gate
(`jacobs1991moe`), recurrent switching linear dynamical systems whose discrete state
depends on the continuous one (`linderman2017rslds`), neural ODEs with learned event
functions that trigger discrete transitions (`chen2021eventfn`), and neural hybrid automata
that infer the number of modes and their transitions without being told
(`poli2021nha`).

**How paper 2 relates.** This is the most important scoping citation the paper is missing,
and it cuts against an over-broad reading of the paper's own claim. Prop. Lipschitz applies
to *Lipschitz* pairs; it does not say "neural networks cannot represent hybrid modes",
because these architectures are not globally Lipschitz-smooth in the relevant sense — a
learned event function or a hard gate reintroduces exactly the unbounded local structure the
proposition requires. The paper's MLP is (as §Limitations already concedes) a probe, and the
right statement is representational-class-relative: smooth function classes cannot realise
the exactly localized geometry, *and* the switched/event-based classes here can — but they
are still subject to the identifiability half, which is learner-independent. That is the
sharper and more defensible version of the paper's claim: no architecture in this list can
infer a mode from a sample that never enters it; what code buys is not expressiveness alone
but the ability to state the rule *exactly* (bit-exact off-mode at $\varepsilon=10^{-9}$),
which a learned gate does not give you. Citing this family also pre-empts the obvious
reviewer objection "just use a switching model".

| Key | Evidence | Confirmed at |
|---|---|---|
| `jacobs1991moe` | DOI `10.1162/neco.1991.3.1.79`, Neural Computation 3(1):79–87 | Crossref |
| `linderman2017rslds` | PMLR v54:914–922 (AISTATS 2017); 6 authors as listed | `proceedings.mlr.press/v54/` |
| `chen2021eventfn` | arXiv `2011.03902`, `journal_ref = ICLR 2021` | arXiv API |
| `poli2021nha` | arXiv `2106.04165`; NeurIPS 2021 proceedings PDF | arXiv API + `proceedings.neurips.cc/paper_files/paper/2021/` |

## 8. Statistical model checking and its sample-complexity guarantees

**What the literature establishes.** SMC replaces exhaustive verification with simulation
plus a statistical test, and — this is the part that matters here — it is explicit about
what the sample size buys. `younes2002acceptance` frames it as sequential acceptance
sampling with stated Type-I/Type-II error bounds; `herault2004apmc` gives the
Chernoff–Hoeffding sample complexity for an $(\epsilon,\delta)$ approximation of a
property's probability; `sen2004blackbox` handles the black-box case where you cannot
resample the system at will; `legay2010smc` surveys the field, including the standing
difficulty that **rare properties need sample sizes that scale like the inverse of their
probability**.

**How paper 2 relates.** This is the literature paper 2's gate belongs to, and it is the
one that supplies the vocabulary the paper is currently reinventing. The gate is an SMC
procedure with hypothesis "the model matches the truth to tolerance $\varepsilon$", run
without error bounds; the $(1-r)^N$ acceptance-failure law is the SMC rare-event problem in
its simplest closed form, and the paper's Wilson intervals are the same
finite-sample-honesty discipline. Two differences are worth stating. First, direction of
concern: SMC bounds the probability of a *wrong verdict about a fixed property*, whereas
paper 2 bounds the probability that the sample *never exhibits the phenomenon in question* —
and then shows the verdict on the property it did test ("matches on sampled transitions") is
correct and useless. Second, consequence: SMC stops at a verdict; paper 2 pushes the verdict
through a planner and shows the loss is not proportional to the residual error but is
adversarially selected (play cost $\approx 1$, below-random return). Citing
`herault2004apmc` also lets the paper state honestly what sample size *would* have caught
the mode at a target confidence, which is a stronger practitioner takeaway than "sample
coverage is the whole game".

| Key | Evidence | Confirmed at |
|---|---|---|
| `younes2002acceptance` | DOI `10.1007/3-540-45657-0_17`, CAV 2002, pp. 223–235 | Crossref |
| `herault2004apmc` | DOI `10.1007/978-3-540-24622-0_8`, VMCAI 2004, pp. 73–84 | Crossref + DBLP (venue VMCAI) |
| `sen2004blackbox` | DOI `10.1007/978-3-540-27813-9_16`, CAV 2004, pp. 202–215 | Crossref |
| `legay2010smc` | DOI `10.1007/978-3-642-16612-9_11`, RV 2010, pp. 122–135 | Crossref + DBLP (venue RV) |

*Note:* LNCS series volume numbers are deliberately omitted from these entries — the APIs
return the DOI and ISBN but not the series volume, and I will not guess one.

## 9. PAC and conformal guarantees for learned dynamics models

**What the literature establishes.** Conformal prediction (`vovk2022alrw`) converts any
predictor into one with distribution-free finite-sample coverage: with exchangeable
calibration data, the predicted set contains the truth with probability at least
$1-\alpha$. This has been carried to learned dynamics and control:
`lindemann2023conformal` builds conformal prediction regions over trajectory predictions
and plans against them; `bortolussi2019npm` learns a monitor that predicts specification
violations and equips it with conformal-style rejection of unreliable predictions;
`majumdar2021pacbayes` gives PAC-Bayes generalisation bounds for control policies across
environments.

**How paper 2 relates.** This is the literature that most directly threatens — and most
directly sharpens — the paper's coverage certificate (Prop. coverage / partition). The
shared premise is the fatal one: **exchangeability.** Conformal coverage holds with respect
to the *calibration distribution*, which is exactly the gate distribution; the planner is
not exchangeable with it (the paper measures that the certified box carries $1.9\%$ of the
exploited planner's queries, $7.8\%$ for the union of level sets). So conformal methods
would certify the same wrong model with the same honest-but-irrelevant guarantee, and saying
so is a stronger result than the paper's current Lipschitz-only framing: the failure is not
an artefact of choosing a metric certificate, it survives the best distribution-free
machinery available. The differences to state: the paper's certificate is a *sup-norm*
statement on a region with an explicit $\varepsilon + 2L\rho$ constant, which conformal
prediction does not give; conversely conformal prediction needs no Lipschitz constant,
which is where paper 2's certificate is weakest (it is vacuous for the mode itself, whose
local Lipschitz constant is unbounded). Citing this family lets the paper say precisely
which guarantee it is *not* claiming.

| Key | Evidence | Confirmed at |
|---|---|---|
| `vovk2022alrw` | DOI `10.1007/978-3-031-06649-8`, book (2nd ed.), Springer 2022 | Crossref |
| `bortolussi2019npm` | DOI `10.1007/978-3-030-32079-9_8`, RV 2019, pp. 129–147; **authors Bortolussi, Cairoli, Paoletti, Smolka, Stoller** | Crossref + DBLP |
| `majumdar2021pacbayes` | DOI `10.1177/0278364920959444`, IJRR 40(2–3):574–593, print Feb 2021 (online 2020-10-03) | Crossref |
| `lindemann2023conformal` | DOI `10.1109/LRA.2023.3292071`, IEEE RA-L 8(8):5116–5123 | Crossref |

## 10. Property-based testing with adaptive / targeted generators

**What the literature establishes.** The known weakness of QuickCheck-style random
generation is that uniform generators rarely reach interesting states, and the field's
answer is to make the generator adaptive. `loscher2017targeted` and
`loscher2018automating` add a search (simulated annealing, then automated tuning) that
steers generation towards inputs maximising a user-supplied utility;
`lampropoulos2017luck` lets generators be *derived from the property itself* so that
constrained inputs are produced by construction rather than by rejection;
`padhye2019zest` combines parametric generators with coverage feedback so that the
generator is guided by what the program actually did.

**How paper 2 relates.** Paper 2 currently cites QuickCheck as though random testing were
the state of the art in that field; it is not, and a reviewer who works on testing will
notice. The accurate positioning is: the paper's gate is the *uniform, non-adaptive* end of
a spectrum this literature has spent a decade moving away from, for exactly the reason the
paper measures — uniform generation misses the rare branch. Every one of these three
techniques has an obvious instantiation for the gate: a targeted generator maximising
"distance travelled toward a mode boundary" (`loscher2017targeted`), a generator derived
from the contract so that mode-entering transitions are produced by construction
(`lampropoulos2017luck`), and coverage-guided rollout mutation where "coverage" is which
branches of the synthesized program executed (`padhye2019zest` — and note that for a *code*
world model, branch coverage of the candidate program is directly measurable, which is a
concrete fix the paper can propose rather than gesture at). The difference from the testing
setting is that there the oracle is a stated property, while the paper's oracle is the true
plant; and paper 2 adds what testing does not study — that the *planner* is the adversary
that finds the untested branch at deployment.

| Key | Evidence | Confirmed at |
|---|---|---|
| `lampropoulos2017luck` | DOI `10.1145/3009837.3009868`, POPL 2017, pp. 114–129 (SIGPLAN Notices mirror `10.1145/3093333.3009868`) | Crossref |
| `loscher2017targeted` | DOI `10.1145/3092703.3092711`, ISSTA 2017, pp. 46–56 | Crossref |
| `loscher2018automating` | DOI `10.1109/ICST.2018.00017`, ICST 2018, pp. 70–80 | Crossref |
| `padhye2019zest` | DOI `10.1145/3293882.3330576`, ISSTA 2019, pp. 329–340 | Crossref |

## 11. Planner-aware / decision-aware model learning

**What the literature establishes.** Prediction loss is the wrong training objective for a
model that will be planned with, and the field has formalised the right one.
`farahmand2017vaml` replaces the maximum-likelihood loss with a *value-aware* loss that
weights model error by how much it perturbs the Bellman update; `farahmand2018itervaml`
makes that iterative as the value function changes; `grimm2020vep` gives the cleanest
statement — the *value equivalence principle*: two models are equivalent if they induce the
same Bellman updates over a set of functions and policies, so a model only needs to be
right in the ways the planner uses it; `schrittwieser2020muzero` is the large-scale
existence proof, a model trained purely for planning utility with no reconstruction
objective at all. Together with `lambert2020objective` (already cited) this is the
literature paper 2 is arguing with.

**How paper 2 relates.** Paper 2's headline is a value-equivalence statement in disguise,
and framing it that way makes it stronger. The gate tests *prediction* equivalence on the
gate distribution; the paper shows that this is neither necessary nor sufficient for value
equivalence, and it exhibits the sufficiency failure in its sharpest possible form — an
artifact that is prediction-equivalent to within $10^{-9}$ everywhere the gate looked and
is nonetheless value-*anti*-equivalent (below-random return, play cost $\approx 1$). Two
differences matter. First, this literature's constructive programme is to *train* for value
equivalence, which requires a value function or a policy at training time; paper 2's setting
has neither at synthesis time — the model is written before the planner runs — so its
prescription is a change of *test distribution* (verify where the planner goes), not a
change of loss. Second, value-equivalence results are about approximation quality within a
smooth parametric class; paper 2's failure is an all-or-nothing missing rule that no
reweighting of a loss can recover from a sample that never touched it. The right sentence
for the paper: value-aware model learning tells you which errors matter; paper 2 shows that
a sampling gate cannot even see the errors that matter most, because the sample and the
planner visit different regions.

| Key | Evidence | Confirmed at |
|---|---|---|
| `farahmand2017vaml` | PMLR v54:1486–1494 (AISTATS 2017) | `proceedings.mlr.press/v54/` |
| `farahmand2018itervaml` | NeurIPS 31 (2018), single author Amir-massoud Farahmand | `papers.nips.cc/paper_files/paper/2018/hash/7a2347d96752880e3d58d72e9813cc14-Abstract.html` |
| `grimm2020vep` | arXiv `2011.03506`; NeurIPS 33 (2020) | arXiv API + `proceedings.neurips.cc/paper/2020/hash/3bb585ea00014b0e3ebe4c6dd165a358-Abstract.html` |
| `schrittwieser2020muzero` | DOI `10.1038/s41586-020-03051-4`, Nature 588(7839):604–609 | Crossref |

## 12. Automata learning / active query learning — the classical analogue

**What the literature establishes.** This is the oldest and cleanest form of paper 2's
identifiability claim. `gold1978complexity` shows that finding a minimum-state automaton
consistent with given data is NP-hard — passive data does not hand you the machine.
`angluin1987learning` gives the positive result and, in doing so, names the exact
ingredient paper 2's gate lacks: L\* learns a regular language in polynomial time from
membership queries **plus an equivalence oracle**, and the equivalence oracle is what
supplies the counterexample that a random sample may never contain. `vaandrager2017model`
is the accessible survey of this becoming an engineering practice, and `settles2012active`
is the general statement that actively chosen queries beat passive samples.

**How paper 2 relates.** Paper 2's Prop. ident is the continuous, hybrid-mode instance of
"the sample cannot identify what it never touched", and Angluin gives the paper its cleanest
one-line framing: **the gate provides membership queries drawn at random and no equivalence
oracle at all.** That is why the loop cannot be made complete by more refinement iterations
— refinement only reacts to counterexamples, and the missing ingredient is the oracle that
produces one. It also frames the paper's own proposed fix correctly: "verify on the
distribution the planner visits" is an attempt to build an approximate equivalence oracle
out of the planner, i.e. to let the adversary that would exploit the model also be the
thing that queries it. The differences: the automata setting has a finite, exactly
identifiable target and exact queries, whereas paper 2's target is a program over a
continuous space with a tolerance $\varepsilon$ and a *stochastic* query distribution, so
the classical polynomial-time guarantee has no direct analogue — which is precisely why the
paper's contribution is a probability law ($(1-r)^N$) rather than a query-complexity bound.
Honest note: a query-complexity result *is* what the geometry-of-repairability follow-up
would need, and this is the literature to build it from.

| Key | Evidence | Confirmed at |
|---|---|---|
| `gold1978complexity` | DOI `10.1016/S0019-9958(78)90562-4`, Information and Control 37(3):302–320 | Crossref |
| `angluin1987learning` | DOI `10.1016/0890-5401(87)90052-6`, Information and Computation 75(2):87–106 | Crossref |
| `settles2012active` | DOI `10.1007/978-3-031-01560-1`, book, Synthesis Lectures on AI and ML, 2012 | Crossref |
| `vaandrager2017model` | DOI `10.1145/2967606`, CACM 60(2):86–95 | Crossref |

---

## Dropped candidates (3) — verification failed or was not obtainable

| Candidate | Topic | Why dropped |
|---|---|---|
| Jin, Aydinoglu, Halm, Posa, "Learning Linear Complementarity Systems" (L4DC 2022) | 6 | Not present in Crossref; the queries returned only other Aydinoglu/Posa complementarity papers. I could not confirm the exact title, author list or venue from a machine-readable authority, so it is out. `parmar2021stiff` covers the same point verifiably. |
| Settles, "Active Learning Literature Survey", Univ. Wisconsin–Madison CS Tech Report 1648 (2009) | 12 | The commonly cited form is an unindexed technical report; I could not verify the report number against an authoritative record. Replaced by the verified 2012 book `settles2012active`. |
| Hjalmarsson, "System identification of complex and structured systems" (European Journal of Control, 2009) | 2 | Recalled but never verified — I did not query it, so it must not be cited. `gevers2005identification` covers the identification-for-control/experiment-design revival with a confirmed DOI. |

## Narrowed, not dropped

* `ljung1999sysid` has **no DOI**. Verification is book-level only (Open Library: author
  Lennart Ljung, ISBN `9780136566953` among the six editions listed). If a DOI-or-nothing
  policy is applied, drop it — `gevers2005identification` and `wagenmaker2020active` carry
  topic 2 on their own.
* LNCS **series volume numbers** are omitted from all eight LNCS entries. The DOI and ISBN
  identify the volume unambiguously; the series number was not returned by any API queried,
  and guessing it is the exact error class this task exists to avoid.
* No page range is recorded for `farahmand2018itervaml`, `grimm2020vep`, `poli2021nha` or
  `chen2021eventfn`: the official NeurIPS/ICLR records give none.
* DBLP's JSON API returned HTTP 500 for most multi-term queries during this session, so it
  was used only as a secondary cross-check (venue names for the RV/VMCAI/IJCAI entries and
  the Bortolussi author list). Crossref-by-DOI is the primary authority throughout.
