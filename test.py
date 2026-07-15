from RAG.ingestion.parser import DocumentParsing 

doc  = DocumentParsing()
text = doc.parse("test.pdf")
print(text)