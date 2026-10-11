# BROCWIN Technical Glossary

Plain-language definitions for the poster session. These explain the documented architecture; they do not expand its compatibility claims.

| Term | Meaning |
| --- | --- |
| Ontology | An account of what something is and how it relates to other things; here, the distinction between application, environment, host, services and research record. |
| Executable | A compiled file containing machine instructions and metadata used to load a program. |
| Execution environment | The instruction engine, interfaces, libraries, resources and services needed for an application to behave. |
| x86 | The processor instruction family used by the inherited client. |
| WebAssembly or Wasm | The browser-hosted instruction format executing this runtime's x86 interpreter; it does not automatically provide Windows APIs. |
| Interpreter | An engine that reads and executes another instruction set; here, original x86 guest instructions. |
| Guest and host | The guest is the inherited application and its expected world; the host is the browser environment executing the compatibility machinery. |
| Compatibility runtime | Software that reconstructs selected behaviors required by an application outside its original environment. |
| Windows API contract | The expected behavior of a Windows interface, including arguments, results, errors, timing and resource lifetime. |
| PE loader | Code that maps Windows Portable Executable images into guest memory and handles imports, relocations and initialization metadata. |
| DLL | A dynamic-link library providing code or data to an application; some libraries remain original guest code and some interfaces are reconstructed. |
| Imports and relocations | Loader operations that connect required functions and adjust address-dependent values when an image is mapped. |
| Mapped execution image | The in-memory application after loading and any documented interventions; distinct from the supplied file on disk. |
| TLS | Thread-local storage: data maintained separately for different execution threads. |
| WebGL and D3D9 | Browser and Windows graphics interfaces respectively; supported operations are translated across their boundary. |
| DirectInput and Win32 input | Windows input interfaces reconstructed from browser physical input in the documented runtime. |
| WebAudio | Browser audio facilities reached through the documented FMOD and DirectSound compatibility path. |
| KOM archive | A game resource container exposed through the retained mount arrangement; possession does not establish redistribution rights. |
| Manifest and range mount | An inventory and a resource mapping that let original code access expected files or portions of archives. |
| Winsock and WebSocket relay | The guest networking interface and browser transport arrangement carrying original packet payloads to native services. |
| Native service | An existing server or database executing outside the browser client. |
| Allocator and free list | A memory manager and its retained list of released allocations; the microbenchmark varies that list's depth. |
| Atomic ownership claim | An indivisible update used to determine who may publish a free operation before accounting for it. |
| Microbenchmark | A narrowly constructed performance test; it cannot by itself establish whole-application speedup. |
| Control and candidate | The retained reference condition and the proposed changed condition; their build and observer identities must stay separate. |
| Cold and warm profile | A fresh experiment-specific browser profile and its reuse; not verified cold and warm machine boots. |
| Frame advance | A recorded progress-counter change, not a verified monitor refresh or complete simulation update. |
| SHA-256 audit | A comparison of recorded file hashes within an enumerated scope; it does not prove correctness, rights or authorship. |
| Observer | Instrumentation that measures and records an experiment; it has its own version, failures and validation requirements. |
| Reproducibility | The ability of another group to restore stated conditions and examine or repeat a result using matching inputs and instruments. |
| Custody | Responsibility for keeping artifacts, permissions, provenance and records available; it can pass to new researchers without erasing attribution. |
| MMO | A massively multiplayer online game whose client depends on external services. |
