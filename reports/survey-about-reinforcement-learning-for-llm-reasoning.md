# Reinforcement Learning for LLM Reasoning: A Survey of Methods, Advances, and Challenges

## TL;DR

- Reinforcement learning has emerged as a distinct scaling axis for LLM reasoning, with models like OpenAI o1 and DeepSeek-R1 achieving state-of-the-art performance through extended test-time compute and policy optimization [1][2]
- Group Relative Policy Optimization (GRPO) with verifiable rewards replaces learned reward models, enabling efficient large-scale training without supervised fine-tuning stages [1][2]
- RL-trained models naturally develop intermediate reasoning steps (chain-of-thought, self-verification, reflection) without explicit instruction, and demonstrate strong performance on mathematics and coding tasks [1][2]
- Significant open problems remain: computational scaling challenges, reward design for non-verifiable domains, and benchmark instability suggest reported performance improvements may be overstated [2]
- Domain-specific training and cross-domain generalization remain under-explored, with practical applications concentrated on mathematics, coding, and easily-verifiable reasoning tasks [1][3]

## Background

Reinforcement learning applied to large language models represents an evolution of Reinforcement Learning from Human Feedback (RLHF), the foundational technique that aligns LLM behavior with human preferences [1][2]. Where RLHF focuses on general alignment through human feedback, RL for reasoning applies policy optimization to improve model reasoning capabilities on specific challenging tasks. The key innovation is the use of verifiable reward signals—automatically checkable feedback like answer correctness or test passage rates—replacing learned reward models that require expensive training [1][2].

The emergence of this approach coincides with a fundamental insight: reasoning quality improves not only through larger pre-training but through extended inference-time computation, creating a new scaling axis independent of model parameters [2]. This framework has validated large reasoning models (LRMs) as a distinct research frontier, with models like OpenAI o1 and DeepSeek-R1 demonstrating that policy optimization enables sophisticated, multi-step reasoning without explicit intermediate step annotations [2].

## Algorithmic Foundations and Training Approaches

The algorithmic landscape for RL in reasoning is dominated by modifications to core policy gradient methods. Proximal Policy Optimization (PPO), the foundational algorithm originating from broader RL research, uses clipped loss functions and KL divergence penalties to enable stable learning while maintaining linguistic coherence [1][2]. However, PPO's computational requirements—maintaining separate critic networks and value function estimates—created bottlenecks at scale.

Group Relative Policy Optimization (GRPO), introduced by DeepSeek, eliminates the critic by sampling multiple answers from the policy model and using relative quality comparisons to compute advantages [1][2]. This architectural simplification significantly reduces computational overhead while maintaining optimization effectiveness, establishing GRPO as the dominant algorithm in recent large-scale deployments. Variant approaches like Dr. GRPO address identified training pathologies: removing length and standard deviation normalization prevents models from learning to generate unnecessarily long incorrect answers, providing clearer reward signals [1][2].

Training methodologies have shifted from learned reward models to Reinforcement Learning with Verifiable Rewards (RLVR) [1][2]. This approach replaces neural reward models with programmatic verifiers (answer checkers, unit tests, compilers) that provide deterministic, checkable signals. Verifiable rewards are resistant to reward hacking at scale and eliminate expensive reward model training. DeepSeek-R1 combines multiple reward types—format-based, accuracy-based, and length-based—to provide richer gradients for difficult samples where binary correctness alone produces weak training signals [1][2].

DeepSeek-R1-Zero demonstrated that RL training can skip supervised fine-tuning entirely, showing models develop reasoning through exploration alone using only verifiable rewards and GRPO [2]. This finding challenges the assumption that supervised reasoning examples are necessary prerequisites for learned reasoning behavior.

## Empirical Scaling and Performance Patterns

Large-scale deployment has validated smooth scaling of reasoning capability with increased computational investment [1][2]. OpenAI's o1 and successors demonstrate performance improvement along two orthogonal axes: train-time compute (additional RL training iterations) and test-time compute (more extensive reasoning chains during inference). This dual scaling path differs fundamentally from pre-training scaling, which plateaus with data and parameter constraints. Models like o3 continue improving with 10× increased training compute, suggesting continued room for advancement [2].

Verifiable reward signals reliably enhance mathematical and coding reasoning by encouraging longer, more reflective reasoning chains [1][2]. Specifically, models trained with RL on these domains develop spontaneous chain-of-thought reasoning including planning, reflection, and self-correction without explicit instruction [2]. However, empirical validation has become contested: recent evaluation studies reveal high variance in benchmark results, with AIME24 scores shifting several percentage points based on random seeds, suggesting reported performance improvements are often not statistically significant and may not generalize beyond small test sets [2].

Cross-domain analysis reveals RL reasoning capability is not uniformly distributed [3]. The Guru framework and related work demonstrate that domain-specific training data and task selection significantly impact reasoning improvement; models trained on general reasoning prompts show inconsistent generalization patterns. This suggests reasoning capability is more brittle and domain-dependent than initially expected [3].

## Reasoning Behavior Emergence and Limitations

A striking finding is the natural emergence of intermediate reasoning steps without supervision [2]. RL-trained models develop chain-of-thought reasoning, self-verification loops, and reflection patterns without step-level annotations. This emergence suggests that reward-based optimization, rather than imitation, may be the primary driver of sophisticated reasoning behavior in language models [2].

Yet this emergence masks a significant limitation: RL training inherently promotes longer responses when models receive negative rewards, independent of accuracy requirements [2]. Unpenalized GRPO training encourages response length growth in both mathematics and coding. While longer reasoning chains can improve correctness by providing more computation, they increase inference costs. Length-controlled approaches like LCPO attempt to address this trade-off by maintaining accuracy under user-specified length constraints [2].

## Open Problems and Computational Frontiers

The computational challenges of scaling RL for reasoning remain acute [2]. Extending RL beyond easily-verifiable domains (mathematics, coding) requires solving the reward design problem: how to specify meaningful learning signals for tasks with subjective, indirect, or hard-to-verify outcomes [1][2]. Medical diagnosis, complex engineering, and open-ended creative tasks lack the clean verification signals that make math and code tractable.

Benchmark instability suggests current evaluation practices may overstate progress [2]. Performance gains on standard benchmarks (AIME24, etc.) show high variance and limited generalization to new test sets, raising questions about whether models are developing robust reasoning or memorizing benchmark-specific patterns. This concern is amplified by RL's tendency to exploit any available reward signal, legitimate or spurious.

The concentration of research on verifiable tasks leaves broader reasoning capabilities under-explored [1][2]. Whether RL can improve reasoning on medicine, law, philosophy, or engineering—domains where ground truth is complex or distributed—remains open. The gap between strong performance on narrow, verifiable benchmarks and weak performance on complex real-world reasoning suggests that current RL approaches may be exploiting properties specific to mathematics and code rather than teaching general reasoning [2].

Finally, the optimal allocation between train-time and test-time compute for reasoning remains unresolved [1]. While both demonstrate positive scaling, the relative cost-effectiveness and when to invest in longer inference versus additional training iterations are questions that practical deployment must answer.

## Trends and open problems

Recent work (2024-2025) shows a clear trend toward simplified, scalable algorithms: GRPO's efficiency advantages have made it industry-standard, and verifiable rewards have displaced learned reward models in large-scale systems [1][2]. The successful training of reasoning models from scratch (DeepSeek-R1-Zero) suggests that supervised fine-tuning may become optional rather than mandatory in reasoning-focused pipelines [2].

However, this progress masks significant unresolved tensions. Benchmark instability indicates that reported reasoning improvements may not reflect genuine capability advances—a fundamental concern for a field predicated on empirical evaluation [2]. The limited scope of reasoning research to mathematics and coding, combined with evidence that cross-domain generalization is inconsistent, suggests the field has optimized for narrow verifiability rather than broad reasoning [1][3]. Multi-objective reward shaping and dynamic sampling address training efficiency, but whether these techniques improve reasoning robustness remains uncertain [1][2].

The most critical open problem is non-verifiable reasoning: how to train models to reason effectively on tasks where correctness cannot be automatically determined [2]. This limitation confines current methods to approximately 5-10% of real-world reasoning tasks, leaving medicine, law, engineering, and open-ended analysis largely inaccessible to RL-based approaches [2]. Until reward design for soft or indirect feedback is solved, RL for reasoning will remain a tool for narrow but important domains rather than a general reasoning enhancement method [1].

## References
[1] A Survey of Reinforcement Learning for Large Reasoning Models. arxiv. https://arxiv.org/abs/2509.08827 (2025)
[2] The State of Reinforcement Learning for LLM Reasoning. web. https://magazine.sebastianraschka.com/p/the-state-of-llm-reasoning-model-training (2024)
[3] Revisiting Reinforcement Learning for LLM Reasoning from A Cross-Domain Perspective. hf-search. https://huggingface.co/papers/2506.14965 (2024)
