# User Guide

## User Roles & Permissions

The application supports three distinct roles with progressive permissions:
- **User**: Restricted to the Dashboard and Chat Assistant views. Standard users can ask questions but cannot manage files or accounts.
- **Knowledge Manager**: Can access the Dashboard, Chat Assistant, and Knowledge Base. They can upload, organize, and delete documents, but cannot manage users.
- **Administrator**: Complete system access. Administrators can access all pages, including the User Management interface to create accounts, deactivate users, and change roles.

## Uploading & Categorizing Documents

Knowledge managers and administrators can upload files (`.pdf`, `.docx`, `.txt`, and `.md`) from the **Knowledge Base** page:
1. Before uploading, select the target **Category** from the dropdown menu (options: `General`, `HR`, `Project-Specific`, `Finance`).
2. Click **Upload** to select and process your document.
3. Once processed, the document's category will be shown in the Knowledge Base table. Chunks from the document are tagged with this category in both the SQLite database and FAISS vector index.

## Chatting & Category Filtering

In the **Chat Assistant** page, you can ask questions grounded on the knowledge base:
1. By default, the system searches all uploaded documents.
2. To restrict search results to a specific domain, select a category (e.g. `HR` or `Project-Specific`) from the **Filter Grounding Source** dropdown at the top of the chat panel.
3. When a filter is selected, the assistant will retrieve chunks only from documents matching that category.
4. Every response lists the source document names and page numbers used to ground the answer. If the search finds no matches in the selected category, the system will inform you that it cannot find enough information.

## User Administration

Administrators can manage users by navigating to the **Users** tab:
- **Create User**: Fill in Email, Full Name, Password, and Role, then click **Create User**.
- **Role Assignment**: Change a user's role in real-time by selecting a role from the dropdown menu.
- **Deactivate/Activate User**: Toggle a user's active status. Deactivated users are immediately blocked from logging in or calling API endpoints.


