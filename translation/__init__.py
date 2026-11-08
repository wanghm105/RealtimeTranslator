from config import TRANSLATION_ENGINE


def create_translator():

    if TRANSLATION_ENGINE == "nllb":

        from translation.nllb_engine import NLLBTranslator

        print("Translation engine: NLLB (fast)")

        return NLLBTranslator()

    from translation.qwen_engine import QwenTranslator

    print("Translation engine: Qwen (LLM)")

    return QwenTranslator()
