# Document Catalog Pattern

The document catalog is a JSON file that maps the customer's entire SharePoint folder structure with metadata. It serves as both documentation and a reference for the agent's instructions.

## File naming

`{alias-lowercase}-dokumentkatalog.json`

Example: `bos-dokumentkatalog.json`, `nmd-dokumentkatalog.json`

## Structure

```json
{
  "kunde": "Customer Name",
  "alias": "ALIAS",
  "sharepoint_site": "https://atea.sharepoint.com/sites/...",
  "sharepoint_hovedmappe": "https://atea.sharepoint.com/sites/.../Shared Documents/Customer Folder",
  "generert": "2026-04-04",
  "total_filer": 0,
  "mapper": [
    {
      "navn": "Folder Name",
      "sti": "Relative/Path/From/Root",
      "antall_filer": 0,
      "beskrivelse": "What this folder contains",
      "undermapper": [
        {
          "navn": "Subfolder Name",
          "antall_filer": 0,
          "beskrivelse": "Subfolder description",
          "nokkeldata": {
            "key": "value extracted from documents"
          },
          "status": "ACTIVE | EXPIRED | ARCHIVED"
        }
      ],
      "sokeord": ["keyword1", "keyword2", "keyword3"],
      "nokkeldata": {
        "key": "value"
      }
    }
  ]
}
```

## Guidelines

- Count actual files in each folder (use glob/ls)
- Extract key data points from documents: agreement numbers, dates, prices, contacts, volumes
- Mark agreement status: ACTIVE for current, EXPIRED for past end date, ARCHIVED for historical
- Include search keywords (sokeord) that help identify what to search for in each folder
- Be thorough — the BOS catalog has 11 main folders with detailed subfolders covering 4,061 files
- Norwegian folder names should be preserved as-is
