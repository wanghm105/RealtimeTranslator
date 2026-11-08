from transformers import AutoTokenizer


model_name = "facebook/nllb-200-distilled-1.3B"


print("Downloading tokenizer...")


tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    src_lang="eng_Latn"
)


tokenizer.save_pretrained(
    "models/nllb-tokenizer"
)


print("Tokenizer ready.")