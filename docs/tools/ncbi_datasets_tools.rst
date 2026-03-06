NCBI Datasets Tools
===================

The NCBI Datasets tools provide comprehensive access to the NCBI
Datasets API, enabling researchers to retrieve gene metadata, genome
assembly information, taxonomy data, and virus genome summaries. These
tools integrate with the official NCBI Datasets v2 API to provide
programmatic access to NCBI's curated biological data.

Overview
--------

NCBI Datasets is a resource that lets you easily gather data from
across NCBI databases. The integration provides **56 tools** covering:

- **Gene data retrieval**: Search genes by ID, symbol, accession, or
  taxon; get dataset reports, product reports, orthologs, and links
- **Genome assembly reports**: Get metadata about genome assemblies,
  annotations, sequences, and revision history
- **Taxonomy information**: Retrieve taxonomic metadata, lineage,
  related IDs, and filtered subtrees
- **Virus genome data**: Access viral genome summaries, annotations,
  and metadata
- **Organelle data**: Access organelle dataset reports
- **Biosample data**: Get biosample reports by accession
- **Download summaries**: Preview download contents before downloading

All tools support pagination for large result sets and return data in
structured JSON format.

**Note**: Some endpoints (particularly SARS-CoV-2 protein/genome
tables) may experience upstream API issues. See `KNOWN_TEST_FAILURES.md
<../src/tooluniverse/data/specs/ncbi/KNOWN_TEST_FAILURES.md>`_ for
details.

Available Tools
---------------

ncbi_datasets_gene_by_id
~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve gene metadata from NCBI Datasets API using NCBI Gene IDs.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - gene_ids
     - int or list
     - One or more NCBI Gene IDs (e.g., 59067 for IL21)
   * - page_size
     - int
     - Maximum results to return (default: 20, max: 1000)
   * - page_token
     - str
     - Token for retrieving next page of results

**Returns:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - success
     - bool
     - Whether the request was successful
   * - data
     - dict
     - Gene metadata from NCBI Datasets
   * - gene_ids
     - list
     - The requested gene IDs
   * - error
     - str
     - Error message if request failed

**Example Usage (Python):**

.. code-block:: python

   from tooluniverse import ToolUniverse
   
   tu = ToolUniverse()
   tu.load_tools()
   
   # Single gene ID
   result = tu.run({
       "name": "ncbi_datasets_gene_by_id",
       "arguments": {"gene_ids": 59067}
   })
   
   # Multiple gene IDs
   result = tu.run({
       "name": "ncbi_datasets_gene_by_id",
       "arguments": {"gene_ids": [59067, 50615], "page_size": 5}
   })

**Example Usage (Command-line):**

.. code-block:: bash

   python -m tooluniverse.tools.ncbi_datasets_gene_by_id \
       --gene_ids 59067 --page_size 1

ncbi_datasets_gene_by_symbol
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve gene metadata from NCBI Datasets API using gene symbols and
taxonomic identifier.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - symbols
     - str or list
     - One or more gene symbols (e.g., 'BRCA1')
   * - taxon
     - str
     - NCBI Taxonomy ID or name (e.g., '9606', 'human')
   * - page_size
     - int
     - Maximum results to return (default: 20, max: 1000)
   * - page_token
     - str
     - Token for retrieving next page of results

**Returns:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - success
     - bool
     - Whether the request was successful
   * - data
     - dict
     - Gene metadata from NCBI Datasets
   * - symbols
     - list
     - The requested gene symbols
   * - taxon
     - str
     - The requested taxon identifier
   * - error
     - str
     - Error message if request failed

**Example Usage (Python):**

.. code-block:: python

   from tooluniverse import ToolUniverse
   
   tu = ToolUniverse()
   tu.load_tools()
   
   # Single gene symbol
   result = tu.run({
       "name": "ncbi_datasets_gene_by_symbol",
       "arguments": {
           "symbols": "BRCA1",
           "taxon": "9606"
       }
   })
   
   # Multiple gene symbols
   result = tu.run({
       "name": "ncbi_datasets_gene_by_symbol",
       "arguments": {
           "symbols": ["BRCA1", "BRCA2"],
           "taxon": "human"
       }
   })

**Example Usage (Command-line):**

.. code-block:: bash

   python -m tooluniverse.tools.ncbi_datasets_gene_by_symbol \
       --symbols BRCA1 --taxon 9606

ncbi_datasets_gene_by_accession
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve gene metadata from NCBI Datasets API using RefSeq RNA or
protein accessions.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - accessions
     - str or list
     - One or more RefSeq accessions (e.g., 'NM_007294.4')
   * - page_size
     - int
     - Maximum results to return (default: 20, max: 1000)
   * - page_token
     - str
     - Token for retrieving next page of results

**Returns:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - success
     - bool
     - Whether the request was successful
   * - data
     - dict
     - Gene metadata from NCBI Datasets
   * - accessions
     - list
     - The requested RefSeq accessions
   * - error
     - str
     - Error message if request failed

**Example Usage (Python):**

.. code-block:: python

   from tooluniverse import ToolUniverse
   
   tu = ToolUniverse()
   tu.load_tools()
   
   # Single accession
   result = tu.run({
       "name": "ncbi_datasets_gene_by_accession",
       "arguments": {"accessions": "NM_007294.4"}
   })
   
   # Multiple accessions
   result = tu.run({
       "name": "ncbi_datasets_gene_by_accession",
       "arguments": {
           "accessions": ["NP_068575.1", "NP_851564.1"]
       }
   })

**Example Usage (Command-line):**

.. code-block:: bash

   python -m tooluniverse.tools.ncbi_datasets_gene_by_accession \
       --accessions NM_007294.4

ncbi_datasets_genome_report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve genome assembly reports from NCBI Datasets API by assembly
accessions.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - accessions
     - str or list
     - Genome assembly accessions (e.g., 'GCF_000001405.40')
   * - page_size
     - int
     - Maximum results to return (default: 20, max: 1000)
   * - page_token
     - str
     - Token for retrieving next page of results

**Returns:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - success
     - bool
     - Whether the request was successful
   * - data
     - dict
     - Genome assembly metadata from NCBI Datasets
   * - accessions
     - list
     - The requested assembly accessions
   * - error
     - str
     - Error message if request failed

**Example Usage (Python):**

.. code-block:: python

   from tooluniverse import ToolUniverse
   
   tu = ToolUniverse()
   tu.load_tools()
   
   # Human reference genome
   result = tu.run({
       "name": "ncbi_datasets_genome_report",
       "arguments": {"accessions": "GCF_000001405.40"}
   })
   
   # Multiple genomes
   result = tu.run({
       "name": "ncbi_datasets_genome_report",
       "arguments": {
           "accessions": ["GCF_000001405.40", "GCF_000001635.27"]
       }
   })

**Example Usage (Command-line):**

.. code-block:: bash

   python -m tooluniverse.tools.ncbi_datasets_genome_report \
       --accessions GCF_000001405.40

ncbi_datasets_taxonomy_metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve taxonomy metadata from NCBI Datasets API using NCBI Taxonomy
IDs or names.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - taxons
     - str or list
     - NCBI Taxonomy IDs or names (e.g., '9606', 'human')
   * - page_size
     - int
     - Maximum results to return (default: 20, max: 1000)
   * - page_token
     - str
     - Token for retrieving next page of results

**Returns:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - success
     - bool
     - Whether the request was successful
   * - data
     - dict
     - Taxonomy metadata from NCBI Datasets
   * - taxons
     - list
     - The requested taxon identifiers
   * - error
     - str
     - Error message if request failed

**Example Usage (Python):**

.. code-block:: python

   from tooluniverse import ToolUniverse
   
   tu = ToolUniverse()
   tu.load_tools()
   
   # By taxonomy ID
   result = tu.run({
       "name": "ncbi_datasets_taxonomy_metadata",
       "arguments": {"taxons": "9606"}
   })
   
   # By common names
   result = tu.run({
       "name": "ncbi_datasets_taxonomy_metadata",
       "arguments": {"taxons": ["human", "house mouse"]}
   })

**Example Usage (Command-line):**

.. code-block:: bash

   python -m tooluniverse.tools.ncbi_datasets_taxonomy_metadata \
       --taxons 9606

ncbi_datasets_virus_genome_summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve virus genome summary information from NCBI Datasets API by
taxon.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - taxon
     - str
     - NCBI Taxonomy ID or name for virus (e.g., '2697049')
   * - refseq_only
     - bool
     - Limit to RefSeq genomes only (default: False)
   * - annotated_only
     - bool
     - Limit to annotated genomes only (default: False)
   * - released_since
     - str
     - Include genomes after date (YYYY-MM-DD format)

**Returns:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - success
     - bool
     - Whether the request was successful
   * - data
     - dict
     - Virus genome summary from NCBI Datasets
   * - taxon
     - str
     - The requested virus taxon identifier
   * - error
     - str
     - Error message if request failed

**Example Usage (Python):**

.. code-block:: python

   from tooluniverse import ToolUniverse
   
   tu = ToolUniverse()
   tu.load_tools()
   
   # SARS-CoV-2 genomes
   result = tu.run({
       "name": "ncbi_datasets_virus_genome_summary",
       "arguments": {"taxon": "2697049"}
   })
   
   # With filters
   result = tu.run({
       "name": "ncbi_datasets_virus_genome_summary",
       "arguments": {
           "taxon": "2697049",
           "refseq_only": True,
           "annotated_only": True,
           "released_since": "2024-01-01"
       }
   })

**Example Usage (Command-line):**

.. code-block:: bash

   python -m tooluniverse.tools.ncbi_datasets_virus_genome_summary \
       --taxon 2697049 --refseq_only

Complete Tool Reference
-----------------------

The following tables list all 56 NCBI Datasets tools organized by
category. Each tool follows the same pattern as the examples above,
using ``tu.run()`` with the tool name and arguments.

Gene Tools (18 tools)
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``ncbi_datasets_gene_by_id``
     - Retrieve gene metadata by NCBI Gene IDs
   * - ``ncbi_datasets_gene_by_symbol``
     - Retrieve gene metadata by symbol and taxon
   * - ``ncbi_datasets_gene_by_accession``
     - Retrieve gene metadata by RefSeq accession
   * - ``ncbi_datasets_gene_id_dataset_report``
     - Get dataset reports by gene IDs
   * - ``ncbi_datasets_gene_id_product_report``
     - Get product reports by gene IDs
   * - ``ncbi_datasets_gene_id_links``
     - Get gene links by gene ID
   * - ``ncbi_datasets_gene_id_orthologs``
     - Get gene orthologs by gene ID
   * - ``ncbi_datasets_gene_accession_dataset_report``
     - Get dataset reports by accession IDs
   * - ``ncbi_datasets_gene_accession_product_report``
     - Get product reports by accession IDs
   * - ``ncbi_datasets_gene_locus_tag_dataset_report``
     - Get dataset reports by locus tag
   * - ``ncbi_datasets_gene_locus_tag_product_report``
     - Get product reports by locus tags
   * - ``ncbi_datasets_gene_taxon``
     - Get gene reports by taxonomic identifier
   * - ``ncbi_datasets_gene_taxon_dataset_report``
     - Get dataset reports by taxonomic identifier
   * - ``ncbi_datasets_gene_taxon_product_report``
     - Get product reports by taxonomic identifier
   * - ``ncbi_datasets_gene_taxon_counts``
     - Get gene counts by taxonomic identifier
   * - ``ncbi_datasets_gene_taxon_annotation_chromosome_summary``
     - Get chromosome summary for taxon annotation
   * - ``ncbi_datasets_gene_symbol_taxon_dataset_report``
     - Get dataset reports by symbol and taxon
   * - ``ncbi_datasets_gene_symbol_taxon_product_report``
     - Get product reports by symbol and taxon

Genome Tools (15 tools)
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``ncbi_datasets_genome_report``
     - Retrieve genome assembly reports by accession
   * - ``ncbi_datasets_genome_accession_annotation_report``
     - Get annotation reports by genome accession
   * - ``ncbi_datasets_genome_accession_annotation_summary``
     - Get annotation summary by genome accession
   * - ``ncbi_datasets_genome_accession_check``
     - Check validity of genome accessions
   * - ``ncbi_datasets_genome_accession_links``
     - Get assembly links by accessions
   * - ``ncbi_datasets_genome_accession_revision_history``
     - Get revision history by genome accession
   * - ``ncbi_datasets_genome_accession_sequence_reports``
     - Get sequence reports by genome accession
   * - ``ncbi_datasets_genome_taxon_dataset_report``
     - Get dataset reports by taxons
   * - ``ncbi_datasets_genome_assembly_name_dataset_report``
     - Get dataset reports by assembly name
   * - ``ncbi_datasets_genome_bioproject_dataset_report``
     - Get dataset reports by bioproject
   * - ``ncbi_datasets_genome_biosample_dataset_report``
     - Get dataset reports by biosample ID
   * - ``ncbi_datasets_genome_wgs_dataset_report``
     - Get dataset reports by WGS accession
   * - ``ncbi_datasets_genome_taxon_checkm_histogram``
     - Get CheckM histogram by species taxon
   * - ``ncbi_datasets_genome_sequence_accession_sequence_assemblies``
     - Get assembly accessions for sequence accession
   * - ``ncbi_datasets_virus_genome_summary``
     - Retrieve virus genome summary by taxon
   * - ``ncbi_datasets_virus_taxon_genome_table``
     - Get virus genome metadata in tabular format

Taxonomy Tools (8 tools)
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``ncbi_datasets_taxonomy_metadata``
     - Retrieve taxonomy metadata by taxonomy IDs or names
   * - ``ncbi_datasets_taxonomy_taxon_dataset_report``
     - Get taxonomic data report by taxonomic identifiers
   * - ``ncbi_datasets_taxonomy_taxon_filtered_subtree``
     - Get filtered taxonomic subtree by taxonomic identifiers
   * - ``ncbi_datasets_taxonomy_taxon_name_report``
     - Get taxonomic names data report by taxonomic identifiers
   * - ``ncbi_datasets_taxonomy_taxon_links``
     - Get external links by taxonomic identifier
   * - ``ncbi_datasets_taxonomy_taxon_related_ids``
     - Get related taxonomic identifiers by taxon ID
   * - ``ncbi_datasets_taxonomy_taxon_image_metadata``
     - Get image metadata by taxonomic identifier
   * - ``ncbi_datasets_taxonomy_taxon_suggest``
     - Get taxonomy names and IDs from partial query

Virus Tools (9 tools)
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``ncbi_datasets_virus_accession_dataset_report``
     - Get virus metadata by accession
   * - ``ncbi_datasets_virus_accession_annotation_report``
     - Get virus annotation report by accession
   * - ``ncbi_datasets_virus_accession_check``
     - Check available viruses by accession
   * - ``ncbi_datasets_virus_taxon_dataset_report``
     - Get virus metadata by taxon
   * - ``ncbi_datasets_virus_taxon_annotation_report``
     - Get virus annotation report by taxon
   * - ``ncbi_datasets_virus_taxon_sars2_protein``
     - Summary of SARS-CoV-2 protein datasets by protein name
   * - ``ncbi_datasets_virus_taxon_sars2_protein_table``
     - Get SARS-CoV-2 protein metadata in tabular format

Organelle Tools (2 tools)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``ncbi_datasets_organelle_accessions_dataset_report``
     - Get organelle dataset report by accession
   * - ``ncbi_datasets_organelle_taxon_dataset_report``
     - Get organelle dataset report by taxons

Biosample Tools (2 tools)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``ncbi_datasets_biosample_accession_biosample_report``
     - Get BioSample dataset reports by accession
   * - ``ncbi_datasets_genome_biosample_dataset_report``
     - Get dataset reports by biosample ID

Download Tools (3 tools)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``ncbi_datasets_gene_id_download_summary``
     - Get gene download summary by GeneID (preview)
   * - ``ncbi_datasets_genome_accession_download_summary``
     - Preview genome dataset download
   * - ``ncbi_datasets_genome_accession_annotation_report_download_summary``
     - Preview genome annotation data download

Utility Tools (1 tool)
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``ncbi_datasets_version``
     - Retrieve service version information

Additional Information
----------------------

**API Rate Limits:**

NCBI Datasets API has usage guidelines. For high-volume requests,
consider:

- Using pagination (page_size, page_token)
- Implementing appropriate delays between requests
- Checking NCBI's usage policies

**Data Sources:**

All data is retrieved from the official NCBI Datasets API v2:
https://api.ncbi.nlm.nih.gov/datasets/v2

**Error Handling:**

All tools include comprehensive error handling:

- HTTP errors are caught and reported
- Missing required parameters return descriptive errors
- Invalid parameters are handled gracefully
- Timeout errors are captured (default: 30 seconds)

**Rate Limits:**

NCBI Datasets API requests are rate-limited:

- Default: 5 requests per second (rps)
- With API key: 10 requests per second (rps)

**Environment Variables:**

- ``NCBI_DATASETS_TIMEOUT``: Set request timeout in seconds (default:
  30)
- ``NCBI_API_KEY``: Your NCBI API key for enhanced access (10 rps)

**Getting an API Key:**

To get enhanced access (10 rps instead of 5 rps):

1. Sign in to your My NCBI account at https://www.ncbi.nlm.nih.gov/
2. Go to Account Settings
3. Scroll to "API Key Management" section
4. Click "Create API Key"
5. Set the ``NCBI_API_KEY`` environment variable:

.. code-block:: bash

   export NCBI_API_KEY=your_api_key_here

For more details, see: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/api-keys/

**Further Reading:**

- NCBI Datasets Documentation: https://www.ncbi.nlm.nih.gov/datasets/docs
- API Documentation: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api
- NCBI Gene Database: https://www.ncbi.nlm.nih.gov/gene

