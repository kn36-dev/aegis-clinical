Why Sqlite instead of a proper relational database like PostgreSQL
- Yes I know that using PostgreSQL allows better database performance, like better concurrency, sharding, indexing, partitioning read and write databases etc, but this project's primary purpose is to demonstrate strong AI Engineering vigor, so the database setup is kept intentionally light-weight.
- It also allows easier reproduction if a repository visitor decides to clone the project and have a go at it.
- In exchange, a proper database setup command will be included in the repository, which is not something commonly required in production systems.

How about database schema storage?
- Yes it is 