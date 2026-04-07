# Coding Conventions

## NO SHARED CODE POLICY

**CRITICAL RULE**: All code in the `pages/` folder must be completely self-contained.

### Requirements:
- **Each page file contains ALL code it needs** - never import from other page files
- **No shared utilities or modules** - copy any needed functions directly into each page file
- **Complete independence** - each page must work without any dependencies on other page files
- **No cross-file references** - never create utils, helpers, or shared modules

### Implementation Guidelines:
- If you need a function that exists in another page, copy it entirely into your current page
- Each page should be able to run independently without any other page files
- All imports should only be from standard libraries or external packages, never from other page files
- When creating new pages, include all necessary utility functions within that single file

### Why This Convention:
- Ensures complete modularity and independence of each page
- Prevents breaking changes when modifying one page affecting others
- Makes debugging and maintenance easier
- Allows pages to be moved or copied without dependencies

**Remember: Each page is a complete, standalone application within the larger project.**