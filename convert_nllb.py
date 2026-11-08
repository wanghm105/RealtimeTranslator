import ctranslate2


converter = ctranslate2.converters.TransformersConverter(
    model_name_or_path="facebook/nllb-200-distilled-1.3B"
)


converter.convert(
    output_dir="models/nllb-ct2",
    quantization="float16",
)


print("NLLB conversion complete.")