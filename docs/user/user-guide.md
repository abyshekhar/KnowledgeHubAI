# User Guide

## Uploading Documents

Knowledge managers can upload PDF, DOCX, TXT, and Markdown files from the Knowledge Base page. Uploaded documents are parsed, cleaned, chunked, embedded, and persisted into the local vector index.

## Chatting

Ask questions in the Chat Assistant page. Answers are generated only from retrieved document context. If the system cannot find enough evidence, it returns:

```text
I could not find enough information in the knowledge base to answer this question.
```

Every answer includes source metadata so users can inspect where information came from.

## Administration

Admins manage users, roles, document access levels, feedback, and deployment configuration. Future LDAP, Active Directory, and SSO adapters can be added behind the existing authentication boundary.

