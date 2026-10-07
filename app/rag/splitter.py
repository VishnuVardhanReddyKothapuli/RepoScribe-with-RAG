import re
from typing import List, Dict, Any
from app.rag.loader import redact

def chunks(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for file in files:
        content = redact(file['content'])
        for start in range(0, len(content), 2400):
            text = content[start:start + 3000]
            if text.strip():
                result.append({
                    'id': f'S{len(result) + 1}',
                    'path': file['path'],
                    'line': content.count('\n', 0, start) + 1,
                    'text': text
                })
    return result
