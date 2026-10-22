# B2 source provenance, license and CVE review

Candidate: com.lambdapioneer.argon2kt:argon2kt:1.6.0, test-only.
AAR SHA256: 38a145241b70a0ad1d0af10732394428f46106e637c2e946a63e2afd7dd3b5d2.
Source tag v1.6.0: 226d943ad1c6344a049c08a437e09688ceb07929.

Wrapper: MIT, copyright Daniel Hugenroth. Preserve upstream notice:
https://github.com/lambdapioneer/argon2kt/blob/v1.6.0/LICENSE
Vendored Argon2 C: CC0-1.0 or Apache-2.0 at recipient's option; preserve
copyright Daniel Dinu, Dmitry Khovratovich, Jean-Philippe Aumasson, Samuel Neves.
https://github.com/P-H-C/phc-winner-argon2/blob/20190702/LICENSE

native-source-provenance.json compares the 20 vendored files to reference
20190702/62358ba2123abd17fccf2a108a301d4b52c01a7c: 19 exact Git blobs,
argon2.h differs in comments/formatting. This identifies source provenance,
not a reproducible-build attestation for the binary AAR. No private fork.
Published AAR has four ABI pairs of native libraries; ELF PT_LOAD p_align=16384.
Actual APK packaging/runtime must be checked separately by the workflow.

AndroidX test runner/monitor/core/ext-junit and appcompat/core are Apache-2.0;
Kotlin stdlib is Apache-2.0, JUnit4 EPL-1.0, Hamcrest BSD-3-Clause. These are
source-license observations, not legal approval. The actual resolved tree,
versions and hashes are the review inventory; verify every transitive license
against upstream/POM before a production ADR. This Draft is not for merging.

CVE status: NOT-VERIFIED until the unchanged baseline security scan has run
against its resolved inventories. A Maven wrapper scan does not certify native
C or its JNI boundary; no 'CVE-free' claim. Any finding must be retained with
component/version/advisory and applicability, not suppressed to force a pass.
A successful scan with HIGH/CRITICAL gate does not prove absence of lower or
unpublished vulnerabilities. Native source maintenance and malformed-input
cost limits remain Leader review concerns. No production library selected.
