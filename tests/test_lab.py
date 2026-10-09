import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import agents
import bootstrap_sources
import check_citations
import research
import tools
from ensure_source_families import ensure_coverage
from normalize_report_structure import normalize_structure
from normalize_source_urls import normalize_sources, normalize_url


class RetryTests(unittest.TestCase):
    def test_retries_then_succeeds_without_sleeping_after_success(self):
        fn = Mock(side_effect=[tools.RetryableError("one"), tools.RetryableError("two"), "ok"])
        with patch("tools.time.sleep") as sleep, patch("tools.random.uniform", return_value=0.25):
            self.assertEqual(tools.with_retry(fn, attempts=3, base=1, cap=10), "ok")
        self.assertEqual(fn.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1.25, 2.25])

    def test_retry_after_is_capped_and_no_sleep_after_last_attempt(self):
        fn = Mock(side_effect=tools.RetryableError("busy", retry_after=99))
        with patch("tools.time.sleep") as sleep:
            with self.assertRaises(tools.RetryableError):
                tools.with_retry(fn, attempts=2, cap=4)
        self.assertEqual(fn.call_count, 2)
        sleep.assert_called_once_with(4)

    def test_non_retryable_exception_is_not_retried(self):
        fn = Mock(side_effect=ValueError("bug"))
        with self.assertRaises(ValueError):
            tools.with_retry(fn, attempts=5)
        fn.assert_called_once_with()


class SourceToolHelpersTests(unittest.TestCase):
    def test_arxiv_normalizes_version_whitespace_and_url(self):
        xml = b"""<?xml version='1.0'?>
        <feed xmlns='http://www.w3.org/2005/Atom'><entry>
          <id>http://arxiv.org/abs/2501.00001v3</id><published>2025-01-02T00:00:00Z</published>
          <title> A\n title </title><summary> Some   evidence. </summary>
        </entry></feed>"""
        response = Mock(content=xml)
        with patch("tools._request_once", return_value=response), patch("tools._wait_for_arxiv_slot"):
            result = json.loads(tools.arxiv_search.invoke({"query": 'all:"world" AND model', "max_results": 3}))
        self.assertEqual(result[0]["id"], "2501.00001")
        self.assertEqual(result[0]["url"], "https://arxiv.org/abs/2501.00001")
        self.assertEqual(result[0]["title"], "A title")

    def test_empty_arxiv_query_never_calls_network(self):
        with patch("tools._request_once") as request:
            self.assertEqual(tools.arxiv_search.invoke({"query": '::: ""'}), "NO RESULTS")
        request.assert_not_called()

    def test_hugging_face_mapping_prefers_ai_summary(self):
        records = tools._hf_records(
            [{"paper": {"id": "2501.1", "title": "T", "summary": "long", "ai_summary": "short",
                         "upvotes": 2, "publishedAt": "2025-01-02T00:00:00Z"}}],
            prefer_ai_summary=True,
        )
        self.assertEqual(records[0]["summary"], "short")
        self.assertEqual(records[0]["url"], "https://huggingface.co/papers/2501.1")

    def test_sse_and_rate_limit_helpers(self):
        sse = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"content":[]}}\n\n'
        self.assertIn("result", tools._json_rpc_payload(sse))
        self.assertTrue(tools._contains_rate_limit({"isRateLimited": True}))
        self.assertFalse(tools._contains_rate_limit({"isRateLimited": False}))

    def test_error_redacts_raw_and_encoded_secret(self):
        secret = "secret+/value"
        error = tools._tool_error(RuntimeError(f"url?exaApiKey=secret%2B%2Fvalue raw={secret}"), secret)
        self.assertNotIn(secret, error)
        self.assertNotIn("secret%2B%2Fvalue", error)
        self.assertIn("[REDACTED]", error)


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            {"n": 1, "url": "https://example.com/a"},
            {"n": 2, "url": "https://example.com/b"},
        ]

    def test_valid_grouped_citations(self):
        report = """# Survey

## Background
Claim [1, 2]. Code `not a citation [9]` and a link [8](https://example.com).

## References
[1] A. web. https://example.com/a (2025-01-01)
[2] B. web. https://example.com/b (2025-01-02)
"""
        self.assertEqual(check_citations.check(report, self.sources), [])

    def test_detects_missing_unused_duplicate_and_wrong_reference(self):
        sources = self.sources + [{"n": 3, "url": "https://example.com/a"}]
        report = """Claim [9].
## References
[1] A. https://wrong.example/a https://second.example/a
[9] Unknown. https://example.com/9
"""
        problems = "\n".join(check_citations.check(report, sources))
        self.assertIn("duplicate source url", problems)
        self.assertIn("[9] cited but missing", problems)
        self.assertIn("source [1] never cited", problems)
        self.assertIn("exactly one URL", problems)
        self.assertIn("reference [9] has no matching source", problems)


class SourceUrlNormalizationTests(unittest.TestCase):
    def test_encodes_validator_delimiters_and_preserves_url_syntax(self):
        url = "https://www.cell.com/fulltext/S2666-3899(25)00218-1?q=a b#part[1]"
        self.assertEqual(
            normalize_url(url),
            "https://www.cell.com/fulltext/S2666-3899%2825%2900218-1?q=a%20b#part%5B1%5D",
        )

    def test_normalizes_copy_without_mutating_original(self):
        source = {"n": 1, "url": "https://example.com/a_(b)", "source": "web"}
        result = normalize_sources([source])
        self.assertEqual(result[0]["url"], "https://example.com/a_%28b%29")
        self.assertEqual(source["url"], "https://example.com/a_(b)")


class SourceFamilyCoverageTests(unittest.TestCase):
    def test_adds_only_missing_family_from_researcher_notes(self):
        report = "# Survey\n\n## Background\nEvidence [1][2].\n"
        sources = [
            {"n": 1, "url": "https://arxiv.org/abs/1", "title": "A", "date": "2025-01-01", "source": "arxiv"},
            {"n": 2, "url": "https://example.com/b", "title": "B", "date": "2025-01-02", "source": "web"},
        ]
        notes = ["""### HF result
- id: 3
- url: https://huggingface.co/papers/3
- date: 2025-01-03
- source: hf-search
- evidence:
  - The evaluated method improves the reported benchmark.
"""]
        repaired, repaired_sources, families = ensure_coverage(report, sources, notes)
        self.assertEqual(families, ["hf-search"])
        self.assertIn("[3]", repaired)
        self.assertEqual(repaired_sources[-1]["source"], "hf-search")
        self.assertEqual(check_citations._body_citations(repaired), {1, 2, 3})

    def test_no_change_when_required_families_are_cited(self):
        report = "Evidence [1][2][3].\n"
        sources = [
            {"n": 1, "url": "https://arxiv.org/abs/1", "source": "arxiv"},
            {"n": 2, "url": "https://huggingface.co/papers/2", "source": "hf-search"},
            {"n": 3, "url": "https://example.com/3", "source": "web"},
        ]
        repaired, repaired_sources, families = ensure_coverage(report, sources, [])
        self.assertEqual((repaired, repaired_sources, families), (report, sources, []))

    def test_relabels_impossible_hf_url_then_repairs_hf_family(self):
        report = "Evidence [1][2][3].\n"
        sources = [
            {"n": 1, "url": "https://arxiv.org/abs/1", "source": "arxiv"},
            {"n": 2, "url": "https://arxiv.org/abs/2", "source": "hf-search"},
            {"n": 3, "url": "https://example.com/3", "source": "web"},
        ]
        notes = ["""### HF
- id: 4
- url: https://huggingface.co/papers/4
- date: 2025-01-01
- source: hf-search
- evidence:
  - Grounded evidence.
"""]
        repaired, repaired_sources, families = ensure_coverage(report, sources, notes)
        self.assertEqual(families, ["hf-search"])
        self.assertEqual(repaired_sources[1]["source"], "web")
        self.assertEqual(repaired_sources[-1]["source"], "hf-search")


class ReportStructureTests(unittest.TestCase):
    def test_normalizes_case_and_future_directions_variant(self):
        case_variant = "# T\n\n## Trends and Open Problems\nText\n"
        future_variant = "# T\n\n## Open Problems\nA\n\n## Trends and Future Directions\nB\n"
        self.assertEqual(normalize_structure(case_variant).count("## Trends and open problems"), 1)
        normalized = normalize_structure(future_variant)
        self.assertEqual(normalized.count("## Trends and open problems"), 1)
        self.assertIn("## Open Problems", normalized)


class BootstrapSourceTests(unittest.TestCase):
    class FakeTool:
        def __init__(self, result):
            self.result = result

        def invoke(self, _arguments):
            return self.result

    def test_builds_three_grounded_anchor_notes(self):
        arxiv = json.dumps([{
            "id": "1", "url": "https://arxiv.org/abs/1", "title": "Arxiv", "published": "2025-01-01",
            "summary": "Arxiv evidence",
        }])
        hf = json.dumps([{
            "id": "2", "url": "https://huggingface.co/papers/2", "title": "HF", "published": "2025-01-02",
            "summary": "HF evidence",
        }])
        web = """Title: Web source
URL: https://example.com/source
Published: 2025-01-03T00:00:00Z
Highlights:
Web source
This sufficiently long sentence is explicit evidence returned by the web search tool for the unit test.
"""
        notes = bootstrap_sources.build_anchor_notes(
            "topic",
            arxiv_tool=self.FakeTool(arxiv),
            hf_tool=self.FakeTool(hf),
            web_tool=self.FakeTool(web),
        )
        self.assertEqual(len(notes), 3)
        combined = b"\n".join(notes.values()).decode()
        self.assertIn("- source: arxiv", combined)
        self.assertIn("- source: hf-search", combined)
        self.assertIn("- source: web", combined)


class ResearchPipelineTests(unittest.TestCase):
    def test_slugify_is_safe_and_bounded(self):
        self.assertEqual(research.slugify("../../World Model"), "world-model")
        self.assertEqual(research.slugify("!!!"), "topic")
        self.assertLessEqual(len(research.slugify("a" * 100)), 60)

    def test_summarize_counts_lead_calls_and_tokens(self):
        messages = [
            {"tool_calls": [{"name": "task"}, {"name": "web_fetch"}],
             "usage_metadata": {"input_tokens": 10, "output_tokens": 4}},
            {"tool_calls": [{"function": {"name": "task"}}],
             "usage_metadata": {"prompt_tokens": 3, "completion_tokens": 2}},
        ]
        result = research.summarize(messages, 1.26, "model")
        self.assertEqual(result["subagent_calls"], 2)
        self.assertEqual(result["tool_calls"], {"task": 2, "web_fetch": 1})
        self.assertEqual(result["tokens"], {"input": 13, "output": 6})
        self.assertEqual(result["elapsed_s"], 1.3)

    def test_save_outputs_validates_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            with patch("research.download", return_value={research.REPORT_PATH: b"", research.SOURCES_PATH: b"[]"}):
                with self.assertRaises(RuntimeError):
                    research.save_outputs(object(), "topic", [], 1, "model", reports)
            self.assertEqual(list(reports.iterdir()), [])

    def test_save_outputs_writes_triplet_and_meta(self):
        source_data = [
            {"n": 1, "url": "https://arxiv.org/abs/1", "source": "arxiv"},
            {"n": 2, "url": "https://huggingface.co/papers/2", "source": "hf-search"},
            {"n": 3, "url": "https://example.com/3", "source": "web"},
        ]
        downloaded = {
            research.REPORT_PATH: b"# Report\n",
            research.SOURCES_PATH: json.dumps(source_data).encode(),
        }
        with tempfile.TemporaryDirectory() as directory, patch("research.download", return_value=downloaded):
            report_path = research.save_outputs(
                object(), "A Topic", [{"tool_calls": [{"name": "task"}, {"name": "task"}, {"name": "task"}]}],
                2.0, "m", Path(directory)
            )
            self.assertTrue(report_path.exists())
            meta = json.loads((Path(directory) / "a-topic.meta.json").read_text())
            self.assertEqual(meta["n_sources"], 3)
            self.assertEqual(meta["source_families"], ["arxiv", "hf-search", "web"])
            self.assertEqual(meta["subagent_calls"], 3)

    def test_save_outputs_records_shared_token_budget(self):
        source_data = [
            {"n": 1, "url": "https://arxiv.org/abs/1", "source": "arxiv"},
            {"n": 2, "url": "https://huggingface.co/papers/2", "source": "hf-search"},
            {"n": 3, "url": "https://example.com/3", "source": "web"},
        ]
        downloaded = {
            research.REPORT_PATH: b"# Report\n",
            research.SOURCES_PATH: json.dumps(source_data).encode(),
        }
        calls = [{"name": "task"}, {"name": "task"}, {"name": "task"}]
        with tempfile.TemporaryDirectory() as directory, patch("research.download", return_value=downloaded):
            research.save_outputs(
                object(), "Budgeted", [{"tool_calls": calls}], 1, "m", Path(directory),
                all_agent_tokens={"input": 123, "output": 45},
            )
            meta = json.loads((Path(directory) / "budgeted.meta.json").read_text())
            self.assertEqual(meta["tokens_all_agents"], {"input": 123, "output": 45})

    def test_empty_topic_returns_usage_error(self):
        self.assertEqual(research.main("  "), 2)


class AgentConfigurationTests(unittest.TestCase):
    def test_shared_token_budget_stops_all_agents_after_cap(self):
        from langchain_core.messages import AIMessage

        budget = agents.SharedTokenBudget(input_limit=10, output_limit=5)
        middleware = agents.SharedTokenBudgetMiddleware(budget)
        state = {"messages": [AIMessage(
            content="x",
            usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
        )]}
        self.assertIsNone(middleware.after_model(state, None))
        self.assertEqual(budget.snapshot(), {"input": 10, "output": 2})
        command = middleware.before_model(state, None)
        self.assertEqual(command["jump_to"], "end")
        self.assertIn("Shared token budget reached", command["messages"][0].content)

    def test_subagent_specs_have_tools_and_limits(self):
        specs = {spec["name"]: spec for spec in agents.build_subagents()}
        self.assertEqual(set(specs), {"researcher", "citation-checker"})
        self.assertEqual(specs["researcher"]["tools"], tools.SOURCE_TOOLS)
        self.assertEqual(specs["citation-checker"]["tools"], [tools.web_fetch])
        self.assertTrue(all(spec["middleware"] for spec in specs.values()))

    def test_lead_agent_receives_todo_limits_backend_and_model(self):
        backend, model = object(), object()
        sentinel = type("GraphSentinel", (), {})()
        with patch("agents.create_deep_agent", return_value=sentinel) as create:
            self.assertIs(agents.build_lead_agent(backend, model), sentinel)
        kwargs = create.call_args.kwargs
        self.assertIs(kwargs["backend"], backend)
        self.assertIs(kwargs["model"], model)
        self.assertEqual(len(kwargs["subagents"]), 2)
        self.assertGreaterEqual(len(kwargs["middleware"]), 4)
        lead_budget_middleware = kwargs["middleware"][-1]
        sub_budget_middleware = kwargs["subagents"][0]["middleware"][-1]
        self.assertTrue(all(spec["middleware"][-1] is sub_budget_middleware for spec in kwargs["subagents"]))
        self.assertIsNot(lead_budget_middleware, sub_budget_middleware)
        self.assertEqual(sentinel._lab_token_budget.snapshot(), {"input": 0, "output": 0})


if __name__ == "__main__":
    unittest.main()
