Why Sqlite instead of a proper relational database like PostgreSQL
- Yes I know that using PostgreSQL allows better database performance, like better concurrency, sharding, indexing, partitioning read and write databases etc, but this project's primary purpose is to demonstrate strong AI Engineering vigor, so the database setup is kept intentionally light-weight.
- It also allows easier reproduction if a repository visitor decides to clone the project and have a go at it.
- In exchange, a proper database setup command will be included in the repository, which is not something commonly required in production systems.

The patient_identity_vault seems to be not properly secured
- Yes, in production systems, the Personally Identifiable Information (PII) must be rigourously protected by: 
   - Encryption of the actual disk
   - AES-256 for the exact columns and the secret key kept in a cloud key management service
   - Secured in isolated virtual private network with no public IP Address
   - Application-Layer Encryption (CLE) to encrypt and decrypt sensitive texts before sending it over the wire
- But it does not add to the AI Engineering experise showcase, so it is currently kept extremely minimal