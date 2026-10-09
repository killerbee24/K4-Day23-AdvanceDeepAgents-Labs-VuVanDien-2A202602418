# LLM Agents and Tool Use: Architectures, Methods, and Challenges

## TL;DR

- LLM agents integrate reasoning with tool use through frameworks like Chain-of-Thought, ReAct, and function calling, enabling models to synergize internal logic with external API interactions [1] [2]
- State-of-the-art benchmarks (GTA, ACEBench, Live API-Bench) reveal significant capability gaps: most LLMs achieve below 25% success on real-world tasks, though interactive agents improve to ~50% [1] [3] [4]
- Identified failure modes include tool selection errors, parameter hallucination, weak multi-step planning, and context length constraints, with smaller models tending to overuse tools while larger models remain overly conservative [2]
- Recent approaches like ToolScope and IRMA improve tool-use accuracy by 12–19% through tool merging, context-aware filtering, and input reformulation [5] [6]
- Open research challenges include API design standards for LLMs, robust multi-step reasoning with dependencies, and scaling from AI-generated benchmarks to real-world user scenarios [1] [3] [2]

## Background

Large language models are increasingly deployed as autonomous agents in production systems, where their effectiveness depends fundamentally on reliable integration with external tools for information retrieval, computation, and action execution. Tool use refers to the ability of an LLM to recognize when external resources are needed, select appropriate tools from available options, generate correct parameters, and interpret results to continue reasoning [2].

Chain-of-Thought (CoT) prompting established the foundational principle that LLMs reason more effectively when provided exemplars showing explicit reasoning steps [7]. ReAct (Reasoning + Acting) extended this by combining written reasoning with actual external system interactions, establishing a framework where models alternate between thought and action cycles [1]. This paradigm shift—from purely internal reasoning to reasoning-with-tools—has become central to modern agentic LLM systems and remains the current state-of-the-art prompting technique to minimize hallucinations while improving reasoning [7].

Function calling provides a concrete operationalization of tool use. Modern reasoning models, trained with reinforcement learning, identify when tool invocation is needed during their reasoning process and pass back instructions for execution [8]. For multi-step tasks requiring tool chains with dependencies, orchestration patterns loop through model responses, executing function calls and feeding results back for continued reasoning until the task completes [8].

## Core Approach Families: Prompting, Learning, and Policy

Tool use in LLMs operates across three primary paradigms [9]. **Prompting-based approaches** treat tool use as a plug-and-play mechanism—models are given tool descriptions and decide when and how to use them without retraining. **Supervised tool learning** fine-tunes models on tool-use demonstrations to improve decision-making and parameter generation. **Reward-driven tool policy learning** trains models using reinforcement learning to optimize tool-use sequences toward task completion.

Among prompting approaches, ReAct and function calling represent the most widely deployed methods. Chain-of-Thought reasoning combined with explicit tool-calling instructions enables transparent multi-step planning. For complex dynamic environments with many interdependent tools, advanced methods reformulate user queries with domain-specific context and tool suggestions; the Input-Reformulation Multi-Agent (IRMA) framework demonstrated 16.1–19.1% improvements over ReAct and function calling on multi-turn tool chains [6]. This suggests that input reformulation—augmenting user queries with domain rules and API context—substantially improves tool selection and parameter generation in constrained environments.

Personal LLM agents introduce architectural considerations for tool integration, addressing how agents integrate personal data, device control, and external services while managing capability, efficiency, and security constraints [10].

## Benchmarking and Empirical Evidence

Three major benchmark families have emerged to evaluate tool-use capabilities at scale. **Live API-Bench** evaluated 10 LLMs and 4 ReAct agents against 2,500+ live APIs across SQL, general operations, and RESTful domains [4]. Results showed baseline task completion of 7–47% across models, with interactive agent settings improving to approximately 50%—a substantial performance gap indicating significant room for advancement [4].

**GTA (General Tool Agents)** introduced a 2024 benchmark with 229 real-world tasks, human-designed queries, executable tool chains across perception, operation, logic, and creativity, and multimodal contextual inputs [1]. Evaluation revealed that GPT-4 completed fewer than 50% of tasks, while most other LLMs achieved below 25% success—demonstrating that capability benchmarks rely critically on task authenticity.

**ACEBench** (January 2025) categorizes tool usage into three methodological types: Normal (basic scenarios), Special (ambiguous or incomplete instructions), and Agent (multi-turn dialogues), providing granular error analysis absent in earlier benchmarks [3].

## Identified Failure Modes and Bottlenecks

Research at EMNLP 2024 decomposed tool-use capability into seven evaluation dimensions and identified specific failure patterns [2]. **Tool decision errors** manifest asymmetrically: smaller models (Qwen-7b, Qwen-14b) over-invoke available tools, while GPT-3.5 errs in the opposite direction, avoiding tool use even when necessary. **Tool selection weakness** is severe—GPT-3.5 fails to call required APIs 77% of the time; Qwen-7b frequently selects wrong tools due to weak specification understanding [2].

**Parameter hallucination** emerges as a widespread failure mode: LLMs hallucinate parameter values without evidence, substitute placeholder values (e.g., "/path/to/image"), or provide imprecise values (country name instead of city). **Sequential planning with dependencies** represents another critical weakness—even GPT-4 achieves success rates below 60% on API chains where results from one call must inform subsequent calls, and open-source models rarely recognize the need to start with foundational APIs [2].

**Context length constraints** cause information loss when API results exceed available context. **Character-level precision errors** in copy-paste tasks (URLs, coordinates, decimal values) remain stubborn challenges [2]. These findings suggest that scaling alone is insufficient; architectural and training innovations are necessary.

## Recent Technical Solutions

**ToolScope** proposes two mechanisms to address tool selection and context constraints [5]. ToolScopeMerger automatically audits and merges redundant tool descriptions, reducing ambiguity in overlapping tools. ToolScopeRetriever ranks and selects only the most contextually relevant tools for each query, directly addressing strict input-context limits in real-world API ecosystems [5].

Evaluation evidence consistently shows that model scaling improves performance across nearly all tool-use dimensions [2]. API design quality and documentation clarity emerge as significant factors—poorly specified APIs, verbose or unclear results, and complex dependencies create additional failure modes [2].

## Trends and open problems

Despite recent progress, LLM tool use remains fundamentally constrained by several unresolved challenges [1] [3] [2].

**Real-world scenario alignment** remains critical: most benchmarks rely on AI-generated evaluation tasks, but GTA findings reveal a significant gap between synthetic queries and authentic user intents with implicit tool requirements and multimodal context [1]. Benchmarks optimized on AI data may not predict real-world performance.

**Multi-step planning and reasoning** exposes a systemic gap—LLMs excel at explaining planned tool sequences but struggle with reliable execution of complex, dependency-rich chains [2]. This "talking versus doing" gap suggests that reasoning ability does not directly translate to planning ability, requiring distinct architectural innovations.

**API design standards for the LLM era** have not been established. Current API design conventions reflect human or program-based consumption; APIs designed specifically for LLM consumption—with clarity, minimal hallucination triggers, and explicit dependency semantics—remain an open research direction [2].

**Multi-turn dialogue and context management** extends beyond single-turn tool use; ACEBench introduces multi-agent interaction evaluation, but maintaining consistency and planning awareness across extended conversations remains largely unresolved [3].

**Robustness to ambiguous instructions** challenges all current models. Special scenarios with incomplete or underspecified parameters expose fundamental brittleness, particularly in open-source models, limiting deployment in user-facing applications where instruction clarity cannot be guaranteed [3].

These challenges collectively suggest that tool-use improvement requires not only scaling models but also reimagining API design, benchmark construction, and agent architectures to close the gap between reasoning and reliable action.

## References
[1] GTA: A Benchmark for General Tool Agents. web. https://proceedings.neurips.cc/paper_files/paper/2024/file/8a75ee6d4b2eb0b777f549a32a5a5c28-Paper-Datasets_and_Benchmarks_Track.pdf (2024)
[2] An Evaluation Mechanism of LLM-based Agents on Manipulating APIs. web. https://aclanthology.org/2024.findings-emnlp.267.pdf (2024)
[3] ACEBench: Who Wins the Match Point in Tool Usage?. hf-search. https://huggingface.co/papers/2501.12851 (2025-01-22)
[4] Live API-Bench: 2500+ Live APIs for Testing Multi-Step Tool Calling. arxiv. https://arxiv.org/abs/2506.11266 (2025-06-12)
[5] ToolScope: Enhancing LLM Agent Tool Use through Tool Merging and Context-Aware Filtering. hf-search. https://huggingface.co/papers/2510.20036 (2026-05-08)
[6] How Can Input Reformulation Improve Tool Usage Accuracy in a Complex Dynamic Environment? A Study on τ-bench. arxiv. https://arxiv.org/abs/2508.20931 (2025-08-28)
[7] Chain-of-Thought and ReAct Prompting Guide. web. https://github.com/GoogleCloudPlatform/specialized-training-content/blob/main/courses/generative_ai/app_dev_llm/cot_react.ipynb (n.d.)
[8] Managing Function Calls With Reasoning Models. web. https://developers.openai.com/cookbook/examples/reasoning_function_calls.md (n.d.)
[9] Agentic Tool Use in Large Language Models: A Survey. web. https://arxiv.org/html/2604.00835 (2026-06-29)
[10] Personal LLM Agents: Insights and Survey about the Capability, Efficiency and Security. hf-search. https://huggingface.co/papers/2401.05459 (2024-05-08)
