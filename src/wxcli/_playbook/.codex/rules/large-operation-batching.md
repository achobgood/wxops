# File Operations — 502 Prevention

502 gateway errors happen frequently on Read, Write, and Edit operations — even on normal-sized files (under 300 lines, under 10KB). This is not a "large file" problem. It happens all the time.

## Hard Rules

- **Always use offset/limit on Read.** Never read a file without setting `limit`. Use 150 lines max per read. Even small files.
- **Never fire parallel Read/Write/Edit calls.** One file operation at a time. Always sequential. No exceptions.
- **Write: avoid for existing files.** Use Edit (sends only the diff). If a full rewrite is truly needed, confirm with the user first.
- **Edit: keep old_string/new_string blocks short.** If replacing a large section (50+ lines), break it into multiple smaller Edit calls.
- **New files over 150 lines: write in chunks.** Write the first 150 lines, then Edit to append the rest.
- **Long replies too.** A reply that would print hundreds of lines (a whole stylesheet, a full listing) also risks a 502: split it across messages or summarize it, and put the full text in a file.

## Why This Exists

502 errors on file operations are the number one reliability problem. They kill operations, lose work, and waste context. This happens constantly, not just on large files. The extra round-trips from sequential chunked operations are trivial compared to recovering from a 502.
