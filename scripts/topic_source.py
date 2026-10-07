"""Only upstream catalogue fields may enter topic embeddings."""
def topic_text(family):
    sections=[family['title'],family['summary']]
    for paper in family['papers']:
        sections.extend([paper['title'],paper['abstract']])
    return '\n\n'.join(s.strip() for s in sections if s.strip())
