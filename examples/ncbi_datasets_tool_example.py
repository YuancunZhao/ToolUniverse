# === ncbi_datasets_tool_example.py ===
# Demo usage of NCBI Datasets tools via ToolUniverse

from tooluniverse import ToolUniverse


def main():
    """
    Demonstrate usage of NCBI Datasets tools for retrieving gene,
    genome, taxonomy, and virus data from NCBI.

    This example demonstrates 56 NCBI Datasets tools covering:
    - Gene data retrieval (by ID, symbol, accession, taxon)
    - Dataset reports, product reports, orthologs, and links
    - Genome assembly reports and annotations
    - Taxonomy metadata and lineage
    - Virus genome summaries and annotations
    - Download summaries
    """
    tu = ToolUniverse()
    # Load default tool categories; includes "ncbi_datasets" via
    # default_config
    tu.load_tools()

    print("=" * 70)
    print("NCBI Datasets Tools Example")
    print("=" * 70)
    print()

    # Example 1: Search for a gene by ID
    print("1. Searching for gene by ID (IL21, gene ID 59067)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_gene_by_id",
            "arguments": {"gene_ids": 59067, "page_size": 1},
        }
    )
    if result.get("success"):
        gene_ids = result['gene_ids']
        print(f"   ✓ Success! Retrieved data for gene ID(s): {gene_ids}")
        if "data" in result and "reports" in result["data"]:
            reports = result["data"]["reports"]
            if reports:
                gene = reports[0].get("gene", {})
                print(f"   Gene Symbol: {gene.get('symbol', 'N/A')}")
                desc = gene.get('description', 'N/A')[:60]
                print(f"   Description: {desc}...")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 2: Search for genes by symbol
    print("2. Searching for gene by symbol (BRCA1 in human)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_gene_by_symbol",
            "arguments": {
                "symbols": "BRCA1",
                "taxon": "9606",
                "page_size": 1,
            },
        }
    )
    if result.get("success"):
        symbols = result['symbols']
        print(f"   ✓ Success! Retrieved data for symbol(s): {symbols}")
        print(f"   Taxon: {result['taxon']}")
        if "data" in result and "reports" in result["data"]:
            reports = result["data"]["reports"]
            if reports:
                gene = reports[0].get("gene", {})
                print(f"   Gene ID: {gene.get('gene_id', 'N/A')}")
                desc = gene.get('description', 'N/A')[:60]
                print(f"   Description: {desc}...")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 3: Search for gene by RefSeq accession
    print("3. Searching for gene by RefSeq accession (NM_007294.4)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_gene_by_accession",
            "arguments": {"accessions": "NM_007294.4", "page_size": 1},
        }
    )
    if result.get("success"):
        accessions = result['accessions']
        print(f"   ✓ Success! Retrieved data for accession(s): {accessions}")
        if "data" in result and "reports" in result["data"]:
            reports = result["data"]["reports"]
            if reports:
                gene = reports[0].get("gene", {})
                print(f"   Gene Symbol: {gene.get('symbol', 'N/A')}")
                print(f"   Gene ID: {gene.get('gene_id', 'N/A')}")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 4: Get genome assembly report
    print("4. Retrieving genome assembly report (Human GRCh38.p14)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_genome_report",
            "arguments": {
                "accessions": "GCF_000001405.40",
                "page_size": 1,
            },
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved genome assembly data")
        if "data" in result and "reports" in result["data"]:
            reports = result["data"]["reports"]
            if reports:
                assembly = reports[0].get("assembly_info", {})
                name = assembly.get('assembly_name', 'N/A')
                print(f"   Assembly Name: {name}")
                level = assembly.get('assembly_level', 'N/A')
                print(f"   Assembly Level: {level}")
                organism = reports[0].get("organism", {})
                org_name = organism.get('organism_name', 'N/A')
                print(f"   Organism: {org_name}")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 5: Get taxonomy metadata
    print("5. Retrieving taxonomy metadata for human (9606)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_taxonomy_metadata",
            "arguments": {"taxons": "9606", "page_size": 1},
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved taxonomy data")
        if "data" in result and "taxonomy_nodes" in result["data"]:
            nodes = result["data"]["taxonomy_nodes"]
            if nodes:
                node = nodes[0]
                taxonomy = node.get("taxonomy", {})
                print(f"   Tax ID: {taxonomy.get('tax_id', 'N/A')}")
                sci_name = taxonomy.get('organism_name', 'N/A')
                print(f"   Scientific Name: {sci_name}")
                com_name = taxonomy.get('common_name', 'N/A')
                print(f"   Common Name: {com_name}")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 6: Get virus genome summary
    print("6. Retrieving virus genome summary (SARS-CoV-2, 2697049)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_virus_genome_summary",
            "arguments": {
                "taxon": "2697049",
                "refseq_only": True,
                "annotated_only": True,
            },
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved virus genome summary")
        if "data" in result:
            print(f"   Taxon: {result['taxon']}")
            # Virus data structure may vary
            if "total_count" in result["data"]:
                print(f"   Total genomes: {result['data']['total_count']}")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 7: Search for multiple genes at once
    print("7. Searching for multiple genes by ID (IL21 & IL21R)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_gene_by_id",
            "arguments": {"gene_ids": [59067, 50615], "page_size": 5},
        }
    )
    if result.get("success"):
        num_genes = len(result['gene_ids'])
        print(f"   ✓ Success! Retrieved data for {num_genes} genes")
        if "data" in result and "reports" in result["data"]:
            reports = result["data"]["reports"]
            print(f"   Number of reports: {len(reports)}")
            for idx, report in enumerate(reports[:2], 1):
                gene = report.get("gene", {})
                symbol = gene.get('symbol', 'N/A')
                gene_id = gene.get('gene_id', 'N/A')
                print(f"   Gene {idx}: {symbol} (ID: {gene_id})")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 8: Get gene dataset report
    print("8. Getting gene dataset report (IL21, gene ID 59067)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_gene_id_dataset_report",
            "arguments": {"gene_ids": 59067, "page_size": 1},
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved gene dataset report")
        if "data" in result and "reports" in result["data"]:
            reports = result["data"]["reports"]
            if reports:
                print(f"   Report type: Dataset report")
                print(f"   Number of reports: {len(reports)}")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 9: Get gene orthologs
    print("9. Getting gene orthologs (IL21, gene ID 59067)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_gene_id_orthologs",
            "arguments": {"gene_id": 59067},
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved gene orthologs")
        if "data" in result and "orthologs" in result["data"]:
            orthologs = result["data"]["orthologs"]
            print(f"   Number of orthologs found: {len(orthologs)}")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 10: Get taxonomy dataset report
    print("10. Getting taxonomy dataset report (human, 9606)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_taxonomy_taxon_dataset_report",
            "arguments": {"taxons": "9606", "page_size": 1},
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved taxonomy dataset report")
        if "data" in result:
            print(f"   Report retrieved successfully")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 11: Get genome annotation report
    print("11. Getting genome annotation report...")
    result = tu.run(
        {
            "name": "ncbi_datasets_genome_accession_annotation_report",
            "arguments": {
                "accession": "GCF_000001405.40",
                "page_size": 1,
            },
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved genome annotation report")
        if "data" in result:
            print(f"   Annotation report retrieved")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 12: Get download summary (preview)
    print("12. Getting download summary for gene IDs...")
    result = tu.run(
        {
            "name": "ncbi_datasets_gene_id_download_summary",
            "arguments": {"gene_ids": 59067},
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved download summary")
        if "data" in result:
            print(f"   Download preview available")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    # Example 13: Get virus dataset report
    print("13. Getting virus dataset report (SARS-CoV-2)...")
    result = tu.run(
        {
            "name": "ncbi_datasets_virus_taxon_dataset_report",
            "arguments": {"taxon": "2697049", "page_size": 1},
        }
    )
    if result.get("success"):
        print("   ✓ Success! Retrieved virus dataset report")
        if "data" in result:
            print(f"   Virus metadata retrieved")
    else:
        print(f"   ✗ Error: {result.get('error', 'Unknown error')}")
    print()

    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print()
    print("Note: This example demonstrates 7 core tools plus 6 additional")
    print("      tools. The full integration includes 56 tools covering")
    print("      genes, genomes, taxonomy, viruses, organelles, biosamples,")
    print("      downloads, and utilities.")


if __name__ == "__main__":
    main()
