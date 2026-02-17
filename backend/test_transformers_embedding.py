import torch
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] # First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

try:
    print("🧪 Testing Transformers Embeddings...")
    model_name = 'sentence-transformers/all-MiniLM-L6-v2'
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    
    sentences = ['Hello world']
    encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
    
    with torch.no_grad():
        model_output = model(**encoded_input)
        
    sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
    sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
    
    embedding = sentence_embeddings[0].tolist()
    print(f"✅ Generated embedding: length {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")
    
except Exception as e:
    print(f"❌ Failed to generate embedding: {e}")
