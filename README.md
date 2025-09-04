# DocumentStudy
## Backlog
1. EPIC: Process documents using Document Intelligence SDK (layout model)
    - TASK: build app/service to run analyze from DocIntel SDK
    - TASK: implement configuration options for document intelligence endpoint (and key?), and model name
    - TASK: implement configuration options for "raw" and "cooked" blob storage
    - TASK: implement request object with string parameter for specific file (blob storage url)
    - TASK: implement request object with bool parameter for markdown format (only works with layout model)
    - TASK: implement request object with list parameter for list of entity names with descriptions (primarily for use with LLM)
    - TASK: capture model output: text lines
    - TASK: capture model output: signatures
    - TASK: capture model output: tables
    - TASK: capture model output: checkbox / selection marks
    - TASK: capture model output: bounding boxes & page layout metadata
    - TASK: implement error handling
    - TASK: implement logging and monitoring of requests / responses
    - TASK: write results back to "cooked" blob storage (or other option)
2. EPIC: Evaluate results
    - TASK: build app/service to run evaluation tests
    - TASK: implement configuration option for actual entities (ground truth)
    - TASK: implement test logic for accuracy
    - TASK: implement test logic to capture performance
    - TASK: implement logic to write test results to repository (file, database, other)
    - TASK: run test
    - TASK: generate evaluation report (summary + detailed mismatches)
3. EPIC: Process documents using Document Intelligence SDK (layout model w/ key/value pairs features parameter)
    - TASK: build app/service to run analyze from DocIntel SDK
    - TASK: implement configuration options for document intelligence endpoint (and key?), and model name
    - TASK: implement configuration options for raw and cooked blob storage
    - TASK: implement request object with parameters for specific file (blob storage url)
    - TASK: implement request object with list of entity names with descriptions (primarily for use with LLM)
    - TASK: capture model output: entity key-value pairs
4. EPIC: Process documents using Document Intelligence SDK (read model)
    - TASK: implement code changes to accommodate 'read model'
    - TASK: capture model output: handwriting
5. EPIC: Process documents using Document Intelligence SDK + LLM
    - TASK: implement prompt template with rules
    - TASK: implement prompt template with placeholders for entities & descriptions (e.g. semantic synonyms)
    - TASK: implement prompt template with placeholder for doc intel text output
    - TASK: implement prompt template with desired output format (JSON schema?)
    - TASK: implement call to LLM
