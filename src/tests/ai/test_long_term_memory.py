from typing import List

import pytest

from sirius.ai.long_term_memory import LongTermMemory, LongTermMemoryDocumentType


# @pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_recollect() -> None:
    long_term_memory: LongTermMemory = await LongTermMemory.remember_from_url("https://arxiv.org/pdf/2303.08774.pdf", LongTermMemoryDocumentType.PDF)
    recollection_list: List[str] = await LongTermMemory.recollect("What are the more advanced capabilities of GPT-4 compared to GPT-3.5", long_term_memory)
    # recollection_list: List[str] = await LongTermMemory.recollect("What are the more advanced capabilities of GPT-4 compared to GPT-3.5", LongTermMemory.model_construct(file_name="https://arxiv.org/pdf/2303.08774.pdf"))
    assert len(recollection_list) > 0
