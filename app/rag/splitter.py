import re
from typing import List, Dict, Any
from app.rag.loader import redact

from app.config import settings

def chunks(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    chunk_size = settings.chunk_size
    step = chunk_size - settings.chunk_overlap
    
    for file in files:
        content = redact(file['content'])
        for start in range(0, len(content), step):
            text = content[start:start + chunk_size]
            if text.strip():
                result.append({
                    'id': f'S{len(result) + 1}',
                    'path': file['path'],
                    'line': content.count('\n', 0, start) + 1,
                    'text': text
                })
    return result
