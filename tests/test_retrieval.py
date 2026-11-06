import tempfile
import unittest
from pathlib import Path

from app.core.errors import IntegrationNotConfigured
from app.retrieval.bm25 import BM25Retriever, tokenize
from app.retrieval.corpus import chunk_documents, load_documents
from app.retrieval.schemas import KnowledgeDocument


def document(doc_id, text, store_ids=None):
    return KnowledgeDocument(
        id=doc_id,
        title="Reference",
        source=f"test://{doc_id}",
        text=text,
        store_ids=store_ids or [],
    )


class RetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_rare_query_term_ranks_the_relevant_document_first(self):
        retriever = BM25Retriever(
            chunk_documents(
                [document("tv", "television glare"), document("ac", "air conditioner drainage")]
            )
        )
        result = await retriever.retrieve("glare", "store-a")
        self.assertEqual([hit.document_id for hit in result.hits], ["tv"])
        self.assertGreater(result.hits[0].score, 0)

    async def test_short_relevant_passage_beats_a_long_diluted_passage(self):
        retriever = BM25Retriever(
            chunk_documents(
                [document("long", "glare " + "filler " * 80), document("short", "glare")]
            )
        )
        result = await retriever.retrieve("glare", "store-a")
        self.assertEqual(result.hits[0].document_id, "short")

    async def test_store_filter_applies_to_both_hits_and_scores(self):
        global_doc = document("global", "glare")
        restricted = document("restricted", "glare " * 40, ["store-b"])
        all_docs = BM25Retriever(chunk_documents([global_doc, restricted]))
        global_only = BM25Retriever(chunk_documents([global_doc]))
        result = await all_docs.retrieve("glare", "store-a")
        baseline = await global_only.retrieve("glare", "store-a")
        self.assertEqual([hit.document_id for hit in result.hits], ["global"])
        self.assertAlmostEqual(result.hits[0].score, baseline.hits[0].score)

    async def test_empty_and_unmatched_queries_do_not_return_arbitrary_hits(self):
        retriever = BM25Retriever(chunk_documents([document("tv", "glare")]))
        for query in ["drainage", "", "?!"]:
            with self.subTest(query=query):
                result = await retriever.retrieve(query, "store-a")
                self.assertEqual(result.status, "no_matches")
                self.assertEqual(result.hits, [])
        self.assertEqual((await BM25Retriever([]).retrieve("TV", "store-a")).status, "empty")

    async def test_deterministic_ties_and_top_k(self):
        retriever = BM25Retriever(chunk_documents([document("b", "glare"), document("a", "glare")]))
        result = await retriever.retrieve("glare", "store-a", top_k=1)
        self.assertEqual([hit.document_id for hit in result.hits], ["a"])

    async def test_hindi_vowel_marks_remain_part_of_search_terms(self):
        self.assertEqual(tokenize("टीवी की दूरी?"), ["टीवी", "की", "दूरी"])
        retriever = BM25Retriever(chunk_documents([document("hindi", "टीवी की दूरी पूछें")]))
        result = await retriever.retrieve("दूरी", "store-a")
        self.assertEqual(result.hits[0].document_id, "hindi")

    def test_chunks_cover_the_document_with_expected_overlap(self):
        chunks = chunk_documents([document("d", "one two three four five six seven")], 5, 2)
        self.assertEqual(
            [chunk.text for chunk in chunks],
            ["one two three four five", "four five six seven"],
        )
        self.assertEqual(chunks[1].chunk_id, "d:0001")

    def test_invalid_corpus_fails_instead_of_silently_disabling_retrieval(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "corpus.json"
            with self.assertRaises(IntegrationNotConfigured):
                load_documents(path)
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(IntegrationNotConfigured):
                load_documents(path)
            duplicate = document("same", "glare").model_dump_json()
            path.write_text(f"[{duplicate},{duplicate}]", encoding="utf-8")
            with self.assertRaises(IntegrationNotConfigured):
                load_documents(path)
