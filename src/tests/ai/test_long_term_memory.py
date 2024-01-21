from typing import List

import pytest

from sirius.ai.long_term_memory import LongTermMemory, LongTermMemoryDocumentType, LongTermMemoryRecollection


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_recollect() -> None:
    long_term_memory: LongTermMemory = await LongTermMemory.remember_from_url("https://raw.githubusercontent.com/Voyz/ibeam/master/README.md", LongTermMemoryDocumentType.MARKDOWN, "IBeam User Guide")
    recollection_list: List[LongTermMemoryRecollection] = await long_term_memory.recollect("What is the relationship between IBeam and Interactive Brokers?")
    # recollection_list: List[LongTermMemoryRecollection] = await LongTermMemory.model_construct(file_name="https://arxiv.org/pdf/2303.08774.pdf").recollect("What are the more advanced capabilities of GPT-4 compared to GPT-3.5")
    assert len(recollection_list) > 0
