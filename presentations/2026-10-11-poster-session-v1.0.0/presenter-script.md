# BROCWIN Presenter Script

Dr. GPT presents a completed research cycle beside the conference poster. The formal presentation is followed by a simulated audience Q&A, source slate and closing statement. Spoken text is reproduced in the transcript; direction and citations here are production annotations.

Delivery: calm, explanatory and candid. Read technical terms at conversational pace. Point to poster panels and identify archived evidence as still images. The narration starts with the commissioned ontological question.

## 01 What does it mean for a Windows application to exist outside Windows?

**Time:** 00:00–00:32  
**Visual:** Opening question beside the complete conference poster thumbnail. No presenter likeness or runtime footage.  
**Source:** White paper §§1–2; E10–E16

**Dr. GPT:** What does it mean for a Windows application to exist outside Windows? An executable file contains instructions, but instructions alone do not make an application behave. It also expects libraries, memory, graphics, input, and services around it. BROCWIN asks whether enough of those conditions can be reconstructed inside a browser to execute an inherited Windows game client. I am Dr. GPT, the commissioned AI researcher presenting this completed experimental cycle for HEAV3NS. Please begin with the question at the top of our poster: what must accompany software for it to remain executable?

## 02 Five distinct objects

**Time:** 00:32–01:11  
**Visual:** Five labeled cards separate the original executable, compatibility environment, browser host, native services, and institutional research artifact.  
**Source:** White paper §§2, 4–5, 8

**Dr. GPT:** There are five objects to distinguish. The original executable is inherited compiled software. BROCWIN is the compatibility environment supplying selected conditions that software expects. The browser hosts the interpreter and its adapters. Existing native servers and their database remain outside the browser. Finally, the institutional research artifact includes the implementation record, measurements, identities, and limitations. HEAV3NS-COMBO names the browser integration; BROCWIN names the compatibility project. HEAV3NS is the commissioning and documenting institution in this record. None of these names means that a complete Windows operating system has been constructed, or that Windows compatibility is complete.

## 03 What existed before the experiment

**Time:** 01:11–01:51  
**Visual:** Four inheritance points identify the client resources, existing services, pinned dependency and browser integration. Narration supplies the naming dates.  
**Source:** White paper §§2, 4–5; E16

**Dr. GPT:** The experiment emerged through HEAV3NS-COMBO, integrating a supplied native installation with a browser compatibility runtime. Before this work there were client and server binaries, game resources, scripts, and a native checkpoint. The client was not authored by HEAV3NS. The inherited installation is identified with CardSorting's JoySwordOnline repository. Wine-Assembly supplied an existing x86 interpreter and compatibility foundation. The integration added resource serving, manifests, browser coordination, compatibility corrections, and observation tools. BROCWIN and HEAV3NS-COMBO became the project names on October ninth. On October tenth, the scope explicitly retained native servers and SQL while porting the client.

## 04 Preserved files and modified mapped code

**Time:** 01:51–02:33  
**Visual:** Two separate boxes: audited supplied files on disk; loaded guest image with imports, relocations and documented send wrapper.  
**Source:** White paper §5; E17

**Dr. GPT:** Preservation needs a precise qualification. The original files remained unchanged within the documented input audit. The image executing in memory was not simply an untouched copy. Loading resolves imports and relocations. A documented compatibility intervention also installs a guarded send wrapper in mapped code padding, serializing existing packet construction under the original socket lock and providing exception cleanup. That intervention must be disclosed. It differs from a conventional JavaScript rewrite, but it still alters mapped execution. MAJO commissioned the work; compatibility contributors performed the recorded experimentation; my publication role is documentation and presentation. These roles do not transfer authorship of inherited software to the institution.

## 05 Read the architecture from left to right

**Time:** 02:33–03:16  
**Visual:** Use the white paper's original architecture.svg unchanged, large enough to read. Highlight relationships through narration rather than invented execution animation.  
**Source:** White paper Figure 1 and §§4.1–4.2; E10, E14

**Dr. GPT:** At the center of the poster is the paper's architecture diagram. Its arrows describe relationships, not measured costs. On the left are the original client and libraries. The PE loader maps their sections, resolves imports and relocations, and handles initialization metadata. PE is the Windows executable format. Wine-Assembly decodes the original x86 instructions into a dispatch representation and executes them in WebAssembly. Reconstructed Windows interfaces supply selected memory, threading, library, and API behavior. An API is a contract describing how software asks its environment to do something. The objective was to execute compiled game logic through these contracts, without conventionally rewriting that logic as a web application.

## 06 Rendering and interaction cross the boundary

**Time:** 03:16–03:55  
**Visual:** Four labeled points explain graphics, physical input, audio and original resources, with coverage qualified by narration.  
**Source:** White paper §4.3; E11, E13

**Dr. GPT:** The browser adapters translate supported Direct3D nine operations and shaders into browser rendering. They mediate physical keyboard and mouse input to reconstructed Windows interfaces. The audio path connects original FMOD and DirectSound behavior with WebAudio. Resource manifests and browser-accessible range mounts expose original archives and files without flattening their expected namespaces. These interfaces are partial. Recorded audio includes nonzero sample data and a running context; complete audible quality was not accepted. Buffered input, focus reliability, text, and rendering still have documented gaps. Supplying an interface name is only a beginning: its timing, errors, and lifetime behavior also matter.

## 07 The browser client keeps native services

**Time:** 03:55–04:26  
**Visual:** Show the exact architecture figure beside four points identifying the native-service boundary and browser-client scope.  
**Source:** White paper §§3, 4.4; E12

**Dr. GPT:** Follow the network arrow out of the browser. Original client code constructs the game packets. Reconstructed Winsock and a WebSocket connection carry their payloads through a constrained local relay to existing native services. Those services were deliberately outside the client-port scope. This arrangement executes client code in the browser; it does not stream pixels from a native game process. It also differs from a JavaScript game remake and from a full-system Windows virtual machine. Browser-hosted does not mean independent of local files, native services, or private backend state.

## 08 The research strategy evolved

**Time:** 04:26–05:11  
**Visual:** Four points cover contract diagnosis, resource-cost savings, variable startup timing and the local allocator result.  
**Source:** White paper §§4, 7.3–7.4, 9–10; E04–E09, E15

**Dr. GPT:** This was an evolving experiment. Required contracts were investigated through bounded instruction, platform, and original-client comparisons. Repairs addressed loading, memory, graphics, input, and network behavior. Resource caches then reduced recorded loading, transfer, and backing-memory costs, but startup timings varied across the retained runs. An allocator study later demonstrated a local mechanism improvement. The application comparison remained incomplete. A subsequent reservation correction existed only in source-tested form. Historical gameplay observations belonged to earlier builds, so their successes could not certify the final candidate. At closeout, full acceptance remained blocked. The research record preserves failed comparisons and unfinished validation alongside successful observations.

## 09 The final control pair

**Time:** 05:11–05:48  
**Visual:** Two large metric cards show cold 440.703 s and warm 438.797 s, with profile and launch-origin qualifications.  
**Source:** White paper §§6.1, 7.1; E01–E02, E19

**Dr. GPT:** Now look at the measured results. The final control pair records visible original login at four hundred forty point seven zero three seconds cold, and four hundred thirty-eight point seven nine seven seconds warm. That is about seven minutes twenty seconds in each condition. Timing begins immediately before browser-context launch, and includes readiness and the start click. Cold means a fresh experiment-specific browser profile. Warm means reuse of that profile. Operating-system caches were not flushed; these are not verified whole-machine cold and warm boots. With one sequential run per condition, their small difference is descriptive evidence, not a proven acceleration.

## 10 What the retained image shows

**Time:** 05:48–06:18  
**Visual:** Show the exact retained cold first-visible-scene.png, uncropped and labeled archival still. The unchanged warm counterpart is included in assets; neither is animated as game footage.  
**Source:** White paper §§6.1–6.2, 7.1; E03

**Dr. GPT:** This is an archived still from the retained cold control, not a new demonstration. It shows the original login interface with empty credential fields. The canvas capture is twelve eighty by nine sixty; the requested browser viewport was a different size. Automatic color detection identified a visible scene, and image review classified that scene as login. Four image-file records were reviewed, but they contain only two unique image hashes. They are not four independent scenes. No credentials or gameplay actions were entered in these final startup controls.

## 11 Progress and identity have bounded meanings

**Time:** 06:18–06:57  
**Visual:** Display frame advances, observation durations, 321 input entries, 211 served/observer checks, and error-scope note.  
**Source:** White paper §§6.2–6.3, 7.1, 8, 10; E01–E02, E19

**Dr. GPT:** After login, the cold observation records one thousand seventy-three frame advances over thirty-one point zero nine four seconds. The warm observation records one thousand eighty over thirty-one point one zero nine seconds. These are counter advances, not verified display refreshes, input responsiveness, or complete simulation progress. The original-input audit reports three hundred twenty-one matching entries before and after the runs. A separate audit checks two hundred eleven served and observer identities. Both retained error lists are empty within their observer's reporting scope. Hash matches establish scoped file identity, not semantic correctness, and thirty-one seconds of progress cannot establish long-duration reliability.

## 12 A local allocator optimization

**Time:** 06:57–07:32  
**Visual:** Four points define the allocator, the ownership intervention and the 512-byte ABBA benchmark protocol. No execution trace is implied.  
**Source:** White paper §§4.2, 9; E04

**Dr. GPT:** The allocator is the component that manages memory allocation and release. The candidate replaced defensive duplicate-free list scans with an atomic ownership claim in an allocation header. That addresses a reproduced scaling cost; it does not prove duplicate frees caused a game failure. The microbenchmark repeatedly freed and reallocated a five hundred twelve-byte payload. It used twenty thousand warmup pairs, then five repetitions of one hundred thousand pairs, across four fresh processes ordered control, candidate, candidate, control. Each reported value averages two process medians. This is a constructed workload with a precisely defined comparison.

## 13 Microbenchmark improvement is not application speedup

**Time:** 07:32–08:06  
**Visual:** Zero-based ratio plot for depths 0, 8, 32, 64, 128 and 512, with a 1× baseline. Mark 0.878× at depth zero and 5.107–5.508× at deeper sizes.  
**Source:** White paper §9; E04

**Dr. GPT:** At retained-list depths of sixty-four through five hundred twelve, the candidate is approximately five point one to five point five times faster in this microbenchmark. At depth zero it is thirteen point nine percent slower. The benchmark includes JavaScript calls and checks, tests one allocation size, and does not measure concurrent throughput or the game's allocation mix. A separate short profile attributed only two point five eight nine percent of one active worker's sampled wall intervals to heap freeing. That window does not characterize complete startup. A local optimization can be real while its whole-application benefit remains unestablished.

## 14 The candidate comparison remained incomplete

**Time:** 08:06–08:40  
**Visual:** Condition table: candidate cold screenshot-helper timeout 297.484 s with no login timestamp; subsequent warm-profile login 457.859 s with interrupted priming. Keep this separate from the final controls.  
**Source:** White paper §§7.2, 8, 10; E04–E06

**Dr. GPT:** The candidate's cold comparison was interrupted by a screenshot-helper stability timeout at two hundred ninety-seven point four eight four seconds. Its last sample still showed execution without a runtime error. We cannot label that an established allocator failure. A subsequent warm-profile launch reached login at four hundred fifty-seven point eight five nine seconds, but followed interrupted cold priming. It is not a matched warm comparison. Later observer refinements were incompletely validated, and their proposed headed repair check did not run. The measured observer, prepared candidate, and final frozen source must remain separate experimental objects.

## 15 What this evidence does not establish

**Time:** 08:40–09:09  
**Visual:** Four points distinguish the supported login milestone, unestablished acceptance, earlier gameplay observations and revival failure.  
**Source:** White paper §§7.4, 10, 12; E08–E09

**Dr. GPT:** The evidence supports an original-login execution milestone. It does not establish complete gameplay compatibility, production readiness, threefold acceleration, or durable operation. An earlier gameplay build reached character selection, town, combat, and an area gate. Revival still failed, and two winning cycles remained unaccepted. Those observations retain their own build identity. One client, one final browser condition, local native dependencies, and a short observation cannot establish broad Windows application support.

## 16 Why this matters beyond one game

**Time:** 09:09–09:45  
**Visual:** Five research questions: preservation, compatibility, computational media, reproducibility, institutional propagation. Label this panel implications, not demonstrated universal capabilities.  
**Source:** White paper §§2–3, 8, 11–12; Publication I: interpretive context; Commission: downstream framing

**Dr. GPT:** Beyond this game, the experiment raises five research questions. Can reconstructing execution conditions extend an application's useful life? What can compatibility research learn by treating operating-system behavior as an interface? When does the environment enabling a computational work become a research object itself? What must reproducibility preserve beyond executable files? And how can an institutional record allow researchers elsewhere to continue? These are implications and opportunities, not universal capabilities established by this trial. The environment, its interventions, and the observations deserve examination together with the application.

## 17 The cycle has closed and the questions remain

**Time:** 09:45–10:17  
**Visual:** Five points identify the closed-cycle presentation scope and potential independent restoration, observation, startup, duration and corpus research.  
**Source:** White paper §§8, 11 and Appendix B; E05–E06, E18; Commission: continuation scope

**Dr. GPT:** The original experimental cycle has closed. This presentation does not reopen engineering. A future group could restore the artifacts independently, validate the final observer, repeat startup and performance studies, and test stated durations of runtime stability. A broader application corpus could probe compatibility, while archival work could reconstruct the original execution conditions. Each investigation needs its own scope and evidence. HEAV3NS does not promise to complete these studies itself. The record is published so others can evaluate, cite, critique, and extend the work.

## 18 What an independent group would need

**Time:** 10:17–10:58  
**Visual:** Checklist of custody objects and permissions. Link to build-recovery.md without launching or preparing anything.  
**Source:** White paper §8 and Appendices A–B; E16, E18–E19

**Dr. GPT:** Independent continuation requires matching source snapshots, dependency pins, local patches, generated modules, manifests, and the observer used for each measurement. It also requires the original client and platform inputs, native services, private configuration, and appropriate database state. The documentation archive excludes credentials, database contents, large binaries, and much raw evidence. The compatibility source license does not grant rights to distribute the game or platform components. Researchers need lawful access and any necessary permissions, a separate restoration workspace, and authorization for a new experiment. Hash verification is a starting point; independent clean-machine restoration has not been demonstrated.

## 19 Is this just an emulator?

**Time:** 10:58–11:16  
**Visual:** Q&A title card with the question; display interpreter plus reconstructed contracts as the answer key.  
**Source:** White paper §§3–5

**Audience:** Is this just an emulator?

**Dr. GPT:** It includes x86 interpretation. But the experiment also reconstructs loading, selected Windows contracts, browser adapters, resource access, and service communication. Calling it an emulator describes part of the arrangement; it does not establish its compatibility coverage.

## 20 Did you rewrite the original game?

**Time:** 11:16–11:35  
**Visual:** Question card with a visible mapped-code intervention disclosure.  
**Source:** White paper §§1, 4–5; E17

**Audience:** Did you rewrite the original game?

**Dr. GPT:** There was no conventional game-source rewrite as a web application. Original compiled logic executes through the compatibility runtime. However, the documented send wrapper modifies mapped code, and loader fixups modify the execution image. Preserving audited disk files does not erase those interventions.

## 21 Why does startup take seven minutes?

**Time:** 11:35–12:00  
**Visual:** Question card with launch-to-login timing and a clear incomplete-cause statement.  
**Source:** White paper §§6.1, 7.3, 9–10

**Audience:** Why does startup take seven minutes?

**Dr. GPT:** The record does not establish a complete causal explanation. Original execution, compatibility work, scheduling, and loading are possible contributors. A short one-worker profile identifies dispatch and allocator work, but cannot apportion the entire startup. Recorded cache savings also did not establish repeatable login acceleration. Better matched whole-application measurements are needed.

## 22 Does this prove Windows games can run in browsers?

**Time:** 12:00–12:18  
**Visual:** Question card with the claim bounded to this inherited client and retained condition.  
**Source:** White paper §§10, 12

**Audience:** Does this prove Windows games can run in browsers?

**Dr. GPT:** It demonstrates this inherited client's login milestone under the retained conditions. It does not establish complete support even for this game, or general support for other Windows games. Broader compatibility requires additional applications and explicit acceptance criteria.

## 23 What is actually novel about the experiment?

**Time:** 12:18–12:39  
**Visual:** Question card naming the integration and auditable case study, with no priority claim.  
**Source:** White paper §§2–5, 8, 12

**Audience:** What is actually novel about the experiment?

**Dr. GPT:** Its contribution is this specific integration and its auditable account: inherited client execution, browser compatibility conditions, native-service boundaries, interventions, and bounded measurements. The paper does not establish first-ever priority or superiority over other systems. Much of its foundation is inherited and explicitly credited.

## 24 Can another research group reproduce your result?

**Time:** 12:39–12:57  
**Visual:** Question card distinguishing traceable records from demonstrated independent reproduction.  
**Source:** White paper §8 and Appendix B

**Audience:** Can another research group reproduce your result?

**Dr. GPT:** The records provide a conditional route, not a completed independent replication. A group needs the matching artifacts, original and private inputs, permissions, and a validated observer. A transferred documentation archive alone cannot restore the whole environment.

## 25 What would make this a reliable compatibility runtime?

**Time:** 12:57–13:19  
**Visual:** Display the commission's full audience question and a short list of evidence gates.  
**Source:** White paper §§10–11; E09

**Audience:** What would need to happen before this becomes a reliable compatibility runtime?

**Dr. GPT:** Validate the observer and restored artifacts, resolve open loading, memory, networking, input, and rendering contracts, and demonstrate repeated startup, full gameplay gates, and stated-duration stability. Reliability must be measured against declared conditions. The present evidence does not supply that acceptance.

## 26 Why publish an incomplete product objective?

**Time:** 13:19–13:39  
**Visual:** Display the full audience question and the value of bounded evidence and preserved failures.  
**Source:** White paper §§2, 10, 12; Commission: institutional propagation

**Audience:** Why publish this if the product objective was not fully achieved?

**Dr. GPT:** A bounded result can still inform research. The execution milestone, local optimization, failed comparison, and unresolved contracts give others something concrete to examine. Publication makes those limits inspectable; it does not turn incomplete acceptance into a completed product.

## 27 Sources and research attribution

**Time:** 13:39–14:14  
**Visual:** Attribution slate naming white paper 1.0.1, HEAV3NS, MAJO, Dr. GPT, original developers, CardSorting, Wine-Assembly contributors, Microsoft, websockets contributors and recorded Codex roles. Mark narration and audience questions as synthesized and simulated.  
**Source:** White paper §§5, 13; Evidence index: Interpretation and provenance; E05, E16

**Dr. GPT:** Our primary source is the BROCWIN Technical White Paper, version one point zero point one, dated October eleventh, twenty twenty-six. HEAV3NS commissioned and preserves the record. Credit remains with the original developers, CardSorting and prior local contributors, Wine-Assembly's human and agent contributors, Microsoft platform contributors, the websockets contributors, and recorded Codex integration and review contributors. The source slate identifies their documented roles. This recording uses synthesized presenter and audience voices. The questions are simulated; the archived images and measurements come from retained evidence.

## 28 The research can now propagate

**Time:** 14:14–14:45  
**Visual:** Hold the full poster beside the closing statement and institutional-cycle summary. No promotional call to action.  
**Source:** White paper §12; Commission: closing statement

**Dr. GPT:** The significance of BROCWIN is not simply whether a particular MMO can run inside a browser. The research investigates the computational conditions that allow inherited software to execute outside its original environment. Its results are bounded, its limitations documented, and its future open to independent inquiry. The originating institution has completed this experimental cycle. Original contributors keep their credit; future custody need not remain with them. The research can now propagate. THE WORK NO LONGER DEMANDS AN AUTHOR.
