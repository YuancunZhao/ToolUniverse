# SV/CNV Analysis Procedures

These procedures show how to collect structural-variant evidence for downstream ACMG overlay routing. They intentionally avoid standalone final ACMG classification.

## Phase 2: Gene Content Analysis

```python
def analyze_gene_content(tu, chrom, sv_start, sv_end, sv_type):
    """Identify and annotate genes affected by the SV."""
    result = {
        "fully_contained": [],
        "partially_disrupted": [],
        "flanking": [],
        "fusion_candidates": []
    }

    for gene in genes_in_region:
        relation = classify_gene_overlap(gene, sv_start, sv_end)
        annotation = annotate_gene_context(tu, gene["symbol"])
        result[relation].append({
            "gene": gene["symbol"],
            "relation": relation,
            "transcripts": gene.get("transcripts", []),
            "annotation": annotation
        })

    return result

def annotate_gene_context(tu, gene_symbol):
    """Retrieve background context; do not assign ACMG evidence here."""
    return {
        "omim": tu.tools.OMIM_search(operation="search", query=gene_symbol, limit=5),
        "gene_validity": tu.tools.ClinGen_search_gene_validity(gene=gene_symbol),
        "dosage": tu.tools.ClinGen_search_dosage_sensitivity(gene=gene_symbol),
        "ncbi": tu.tools.NCBIGene_search(term=gene_symbol, organism="human")
    }
```

## Phase 3: Dosage Sensitivity Assessment

```python
def assess_dosage_sensitivity(tu, gene_symbols):
    """Return dosage context for route planning."""
    rows = []
    for gene_symbol in gene_symbols:
        dosage = tu.tools.ClinGen_search_dosage_sensitivity(gene=gene_symbol)
        validity = tu.tools.ClinGen_search_gene_validity(gene=gene_symbol)
        rows.append({
            "gene": gene_symbol,
            "dosage_source": "ClinGen",
            "dosage_result": dosage,
            "gene_validity": validity,
            "route_candidate_only": True
        })
    return rows
```

## Phase 4: Population and Overlap Assessment

```python
def assess_population_and_overlap(tu, chrom, sv_start, sv_end, sv_type):
    """Collect frequency and source-overlap evidence for routing."""
    population = query_population_sv_sources(tu, chrom, sv_start, sv_end, sv_type)
    source_matches = query_clinical_sv_sources(tu, chrom, sv_start, sv_end, sv_type)

    candidate_routes = []
    if population.get("high_frequency_signal"):
        candidate_routes.append("population_frequency_bundle: BA1/BS1/benign-context review")
    if population.get("rare_or_absent_signal"):
        candidate_routes.append("population_frequency_bundle: PM2 absence/rarity review")
    if source_matches:
        candidate_routes.append("literature_functional_bundle: PP5/BP6 source review before fan-out")

    return {
        "population": population,
        "source_matches": source_matches,
        "candidate_routes": candidate_routes
    }
```

## Phase 5: Route Candidate Generation

```python
def generate_sv_route_candidates(sv_summary):
    """Generate ACMG overlay routes without assigning evidence strength."""
    routes = ["cnv_sv_bundle"]

    if sv_summary.get("lof_like_consequence"):
        routes.append("consequence_lof_bundle -> tooluniverse-acmg-pvs1-lof-decision-tree-refinement")
    if sv_summary.get("protein_length_change"):
        routes.append("protein_length_bundle -> tooluniverse-acmg-pm4-bp3-protein-length-refinement")
    if sv_summary.get("frequency_context"):
        routes.append("population_frequency_bundle")
    if sv_summary.get("de_novo_context"):
        routes.append("clinical_observation_bundle -> tooluniverse-acmg-de-novo-evidence-refinement")
    if sv_summary.get("segregation_context"):
        routes.append("clinical_observation_bundle -> tooluniverse-acmg-pp1-segregation-refinement")
    if sv_summary.get("case_enrichment_context"):
        routes.append("literature_functional_bundle -> tooluniverse-acmg-ps4-case-enrichment-refinement")
    if sv_summary.get("functional_assay_context"):
        routes.append("literature_functional_bundle -> tooluniverse-acmg-ps3-bs3-functional-assay-refinement")

    return {
        "candidate_acmg_routes": routes,
        "final_classification_status": "not_final_acmg_classification"
    }
```

## Phase 6: Literature Search

```python
def comprehensive_literature_search(tu, genes, sv_type, phenotype=None):
    """Search literature for route-triggering evidence."""
    literature = []
    for gene in genes:
        dosage_papers = tu.tools.PubMed_search_articles(
            query=f'"{gene}" AND (haploinsufficiency OR triplosensitivity OR dosage sensitivity OR deletion OR duplication)',
            max_results=20
        )
        case_papers = tu.tools.PubMed_search_articles(
            query=f'"{gene}" AND "{sv_type}" AND (case OR cohort OR segregation OR de novo)',
            max_results=15
        )
        literature.append({
            "gene": gene,
            "dosage_papers": dosage_papers,
            "case_papers": case_papers,
            "route_candidate_only": True
        })

    return {"gene_literature": literature}
```

## Phase 7: Hand Off

Pass the output to `tooluniverse-acmg-variant-classification`:

```python
handoff = {
    "sv_evidence_summary": sv_summary,
    "bundle": "cnv_sv_bundle",
    "candidate_acmg_routes": candidate_routes,
    "requires_overlay_route_audit": True,
    "requires_evidence_compatibility_resolution": True,
    "final_classification_status": "draft_until_acmg_overlay_combine"
}
```
