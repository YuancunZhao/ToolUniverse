# Known Test Failures - NCBI Datasets Tools

## Overview

This document tracks test failures caused by **upstream NCBI API issues**.

**Status**: All 53 tools pass 100% (0 xfail, 0 failures)
**Last Updated**: 2026-03-06

## Fixes Applied

### Empty Response Handling (fixed)
All tools now handle empty API responses (200 OK with no body) gracefully,
returning `{}` instead of crashing on `response.json()`.

### Required Parameter Validation (fixed)
All path-parameter tools now validate required parameters before making
API calls, returning clear error messages like `` `taxon` is required ``
instead of generic `'NoneType' object is not iterable` errors.

## Removed Tools (upstream NCBI API issues)

The following 3 tools were removed because their NCBI endpoints return
500/504 errors or reject valid query parameters. They can be re-added
when NCBI fixes these server-side issues.

### 1. NCBIDatasetsVirusTaxonSars2ProteinTool

NCBI's `/virus/taxon/sars2/protein/{proteins}` endpoint returns 500/504
for most optional filter parameters (annotated_only, released_since,
host, pangolin_classification, geo_location, etc.).

### 2. NCBIDatasetsVirusTaxonSars2ProteinTableTool

Same endpoint as above, table format variant. The `table_fields` query
parameter is also rejected despite being in the OpenAPI spec.

### 3. NCBIDatasetsVirusTaxonGenomeTableTool

The `/virus/taxon/{taxon}/genome/table` endpoint rejects the
`table_fields` query parameter despite being in the OpenAPI spec.

## Related Links

- NCBI Datasets API v2: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/
- Rate Limits: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/api-keys/
