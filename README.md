# DocumentStudy
## Backlog
1. EPIC: Process documents using Document Intelligence SDK (layout)
    - TASK: build app/service to run analyze from DocIntel SDK
 - TASK: implement configuration options for document intelligence endpoint (and key?), and model name
 - TASK: implement configuration options for raw and cooked blob storage
 - TASK: implement request object with parameters for specific file (blob storage url)
 - TASK: implement request object with list of entity names with descriptions (primarily for use with LLM)
2. EPIC: Evaluate results
 - TASK: build app/service to run evaluation tests
 - TASK: implement configuration option for actual entities
 - TASK: implement logic to write test results to repository (file, database, other)
3. EPIC: Process documents using Document Intelligence SDK (read)
 - TASK: implement code changes to accommodate 'read model'
4. EPIC: Process documents using Document Intelligence SDK + LLM
 - TASK: implement prompt template with rules and placeholder for text output
 - TASK: implement call to LLM 
