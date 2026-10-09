# World Models: A Survey of Architectures, Applications, and Open Challenges

## TL;DR

- World models are learned representations that predict how environments evolve, enabling planning, imagination, and embodied AI by compressing observations into latent dynamics [1][2]
- Five major architectural families (VAE-based, Transformer, Diffusion, JEPA, Abstract) demonstrate fundamental tradeoffs: RSSM excels in online control, Transformers extend context, Diffusion achieves visual fidelity, JEPA provides robustness, each with distinct limitations [3][4]
- Recent breakthroughs (2024) scale world models to 1B parameters for navigation and robotics, demonstrating zero-shot embodied capabilities and emergence of 3D environment generation [5][6]
- Critical open problems persist: compounding prediction errors over long horizons, visual hallucinations masking physical inconsistency, fragmented evaluation metrics conflating appearance with executability, and gaps between reconstruction quality and planning utility [7][8]

## Background

### Definition and Scope

A world model is a learned system that internally represents how environments change and evolve. Formally, recent work defines neural network world models as systems where simple functions (e.g., linear probing) can recover a homomorphic image of the data-generating process, with the additional requirements that the model must be learned rather than trivially available, emergent rather than explicitly required, and causally complete in determining network outputs [2]. The field encompasses two complementary perspectives: constructing representations to understand mechanisms, and predicting future states to enable simulation and planning [2].

The foundational concept dates to Jürgen Schmidhuber's 1990 technical report "Making the World Differentiable," which introduced recurrent neural networks for learning environmental dynamics and enabling gradient-based policy learning [9]. The modern era began with Ha and Schmidhuber's 2018 "World Models" paper, which pioneered decomposing world model architectures into distinct components including a vision component for observation compression and a memory component for temporal dynamics using VAE and RNN [1].

### Core Theoretical Frameworks

**Model-Based Reinforcement Learning (MBRL)** frames world models as solutions to three interconnected problems: learning state representations from high-dimensional observations, learning state-to-state transition dynamics, and planning effectively with learned models [10]. The central advantage is sample efficiency through reduced real environment interactions, offset by model error accumulation over rollout horizons [10].

**Joint-Embedding Predictive Architectures (JEPA)** represent a modern alternative to generative reconstruction, predicting representations rather than pixels to avoid wasting model capacity on task-irrelevant details [11]. JEPA requires anti-collapse mechanisms (exponential moving average encoders or regularization) and unifies contrastive self-supervised learning with implicit planning [11].

**Latent Space Dynamics** compress high-dimensional observations into compact latent vectors where dynamics are modeled, reducing computational cost and enabling fast imagination of trajectories [3]. The critical design challenge is ensuring latent geometry preserves task-relevant topology and supports decision-making [12].

## Architectural Families and Performance Tradeoffs

World model architectures cluster into five distinct families, each addressing different bottlenecks across prediction accuracy, latency, visual fidelity, and robustness.

### VAE-Based Recurrent State-Space Models

The Recurrent State-Space Model (RSSM) decomposes latent state into deterministic recurrent components (GRU hidden state h_t capturing reliable memory) and stochastic samples (z_t encoding uncertainty), enabling both consistent long-term memory and multimodal prediction [3]. The Dreamer series exemplifies this family: Dreamer V1 (2020) introduced actor-critic training in imagined latent space; DreamerV2 (2021) added categorical latents and KL rebalancing; DreamerV3 (Nature 2025) outperforms specialized methods across over 150 diverse tasks with a single configuration using robustness techniques based on normalization, balancing and transformations [13].

**Strengths**: O(1) per-step inference latency independent of sequence length, analytical differentiability for gradient-based planning, and proven performance on Atari and embodied control tasks [13].

**Weaknesses**: Limited long-term memory due to GRU bottleneck (effective context ~50-100 steps), autoregressive error accumulation, and teacher forcing during training creating inference distribution gap [4].

**Variants**: Clockwork VAE (2021) adds hierarchical temporal abstraction at different clock speeds, improving long-horizon prediction from 150 frames to 400+ frames on Minecraft navigation; LeWAM (2026) replaces RSSM entirely with bidirectional transformers on decoder-free JEPA latents [14].

### Transformer-Based Token Models

Transformer-based world models tokenize observations with VQ-VAE and model sequence dynamics autoregressively with causal masking [4]. IRIS (ICLR 2023) uses 16 tokens per frame; STORM (NeurIPS 2023) reduces to single-token design achieving 126.7% average human-normalized score on Atari 100k; Dreamer 4 (Sept 2025) replaces RSSM entirely with transformer dynamics, achieving 100× data efficiency improvement on offline RL [15].

**Strengths**: Parallel training across sequences (vs. sequential RSSM), exposure to full history without GRU bottleneck, natural handling of longer contexts, and STORM exceeding RSSM on long-horizon prediction benchmarks [4].

**Weaknesses**: Quadratic O(T²) computational scaling with sequence length, higher inference latency than recurrent models, and higher data requirements for convergence [4].

### Diffusion-Based Video Generators

Iterative denoising with 10-100 steps conditioned on historical frames and actions achieves state-of-the-art visual fidelity [16]. Sora (OpenAI, 2024) generates up to 1 minute of high-fidelity variable-resolution video; DIAMOND (NeurIPS 2024) achieves 1.46 human-normalized score on Atari with superior visual realism; Cosmos and Genie 2 demonstrate multi-domain photorealistic generation [5][6].

**Strengths**: Superior visual fidelity and photorealism, handling complex visual phenomena (motion blur, lighting changes), and demonstrated scaling across domains [16].

**Weaknesses**: Object persistence problems—independent per-frame denoising causes identity and position drift despite high per-frame quality; 10-100 steps per frame prohibit online control; non-differentiable sampling prevents gradient-based planning; visual plausibility does not imply physical executability [7][16].

**Critical Finding**: Empirical evaluation via RoboWM-Bench reveals visual metrics (PAI-Bench FVD/FID) and execution success are uncorrelated—state-of-the-art video models saturate perceptual metrics while execution success drops dramatically in complex manipulation [7].

### Joint-Embedding Predictive Architectures

V-JEPA (2024, 1.2B parameters) and V-JEPA 2 (2025) predict masked future observations in representation space without reconstruction, using asymmetric encoders and stop-gradients to prevent collapse [17]. V-JEPA 2-AC adds action conditioning through block-causal attention, enabling control-conditioned prediction [18].

**Strengths**: Exceptional robustness to distribution shift—V-JEPA 2 degrades most gracefully under pixel corruption, occlusion, and temporal reversal compared to reconstruction models; encodes arrow of time as causal concept rather than invariance; achieves state-of-the-art on visual understanding benchmarks while supporting zero-shot robot planning [17][18].

**Weaknesses**: Risk of discarding task-critical unpredictable state (micro-contact, friction, occluded information, fine geometry); less established control track record vs. RSSM; action conditioning (V-JEPA 2-AC) recent and less mature [18][19].

**Representation Differences**: Fundamental training objective difference—Dreamer targets control-sufficient latent space; JEPA targets representation-learning objectives filtering unpredictable details; action treated explicitly in Dreamer, implicitly in V-JEPA, explicitly emerging only in V-JEPA 2-AC [18].

### Physics-Informed and Hybrid Approaches

Recent work augments neural dynamics with physics constraints (symplectic integrators, conservation laws) to enforce physical consistency [20]. Symplectic evolution of learned energy preserves geometry of conservative dynamics, maintaining bounded behavior over long rollouts vs. unconstrained neural drift; residual physics combines first-principles models with learned residual corrections capturing unmodeled dissipation [20][21].

## Recent Advances and Applications (2023-2024)

### Foundation Models for Embodied AI

**Genie 2** (Google DeepMind, December 2024) generates action-controllable 3D environments from single text or image prompts, with emergent capabilities in object interactions, character animation, physics simulation, and multi-agent behavior [5]. Zero-shot agent evaluation in unseen Genie 2 environments addresses the training bottleneck for general embodied AI [5].

**Navigation World Models** (December 2024) scale conditional diffusion transformers to 1B parameters with linear complexity (CDiT architecture), achieving 4× fewer FLOPs than standard approaches while improving performance; state-of-the-art visual navigation via MPC and trajectory ranking [22].

**π₀** (Google DeepMind) combines vision-language models with flow-matching for 50 Hz continuous dexterous control, trained on 10,000+ hours from 7 robot platforms, demonstrating zero-shot laundry folding, table cleaning, and box assembly with cross-embodiment transfer [23].

### Robotics and Manipulation

**PIVOT-R** (NeurIPS 2024) predicts task-relevant waypoints rather than frame-by-frame trajectories, achieving 19.45% relative improvement over state-of-the-art on SeaWave manipulation benchmark with 28× efficiency improvement through asynchronous hierarchical execution [24].

**GenRL** (NeurIPS 2024) connects vision-language embeddings with generative world model latents without language annotations, enabling multi-task generalization across locomotion and manipulation; demonstrates strong vision-style generalization across drawings, realistic images, and camera viewpoints [25].

**Humanoid Locomotion as Next Token Prediction** (NeurIPS 2024) demonstrates real-world humanoid walking in San Francisco zero-shot using autoregressive transformers trained on 27 hours of sensorimotor sequences from simulation, motion capture, and YouTube, suggesting sequence modeling as promising approach for real-world control [26].

### Video Generation and Representation Learning

**Sora** (OpenAI, February 2024) generates up to 1 minute of variable-resolution video with emergent world simulation properties including 3D consistency, long-range coherence, object permanence, and understanding of world interactions [27]. However, Sora systematically violates physical laws—glass shattering before impact, objects disappearing between frames—and lacks causal reasoning capacity for active intervention [28].

**iVideoGPT**, **AVID**, and **Pandora** demonstrate token-based and diffusion-based approaches to scalable video generation with different latent factorizations [29].

### Datasets and Foundation Models

Large-scale annotated robot data now enables transfer learning: **AgiBot World** (900k sequences), **DROID** (125k demonstrations), **OmniWorld** provide action-annotated video for training embodied foundation models [30]. **WorldCoder** (NeurIPS 2024) structures world knowledge as Python programs, enabling sample-efficient learning and fast adaptation to new dynamics [31].

## Evaluation and Benchmarks

### Fragmented Metrics

The field lacks unified benchmarking: different systems optimize for video realism (FVD, FID, LPIPS, PSNR), dynamics accuracy (action-conditioned prediction), physics fidelity, or embodied task success [32]. Dreamer achieves human-level Atari performance (88/100 Performance Index) with universal hyperparameters; DIAMOND achieves 1.46 HNS on Atari 100k with superior visual metrics; Sora generates impressive video while violating physics [27][32].

### The Executability Gap

Critical empirical finding: visual fidelity and embodied executability are uncorrelated [7]. RoboWM-Bench converts generated videos to robot actions via inverse dynamics, validating in simulation. Recurring failures include inaccurate contact prediction, unrealistic object deformation, and geometric distortions in long-horizon interactions [7]. This reveals fundamental mismatch between perceptual and control metrics—models optimizing for appearance rather than physics cannot reliably support planning.

### Robustness Evaluation

V-JEPA 2 demonstrates graceful degradation under corruption, occlusion, and temporal reversal; uniquely encodes arrow of time (DSCS 3-10× higher than baselines); preserves class structure under occlusion where VideoMAE and VideoPrism fail [17]. This suggests representation robustness as critical benchmark dimension orthogonal to visual quality.

## Open Problems and Limitations

### Compounding Prediction Errors

One-step prediction errors compound exponentially over horizons, particularly in unstable dynamics where sensitivity L > 1 yields error growth as L^H [32]. Small 1cm position errors become catastrophic within 5-10 steps of autoregressive rollout [32]. This structural problem applies across all families: even near-zero one-step loss fails within 5-10 steps due to recursive error feedback [32].

Graph world models exhibit topology-dependent error amplification dependent on spectral radius and layer weights, creating coupled node-edge failures absent in vector-state models [33].

### Hallucinations and Physical Inconsistency

Visual realism masks fundamental failures: Sora generates plausible videos while violating invariant physical laws—objects disappearing, causality reversed—with only passive generation capacity lacking causal reasoning for intervention [28]. The distinction between perceptual hallucinations (aesthetic blurring) and dynamical hallucinations (law-violating plausibility) reveals visual appearance metrics miss critical failures [28].

Some models revert to kinematic imagination rather than dynamic understanding, failing to capture friction-dependent gait collapse despite predicting plausible pixels, particularly beyond embodiment gait periods [34].

### Representation Learning Challenges

Latent collapse occurs where distinct observations map to identical codes with information loss; representation drift occurs where latent spaces shift during training [32]. True disentanglement remains unresolved despite decades of effort [32]. Distributed representations mean each feature partially encodes across multiple latent variables, preventing direct mapping to physical quantities [12].

Safety-relevant information gaps arise when partial observability fails to preserve constraint-critical state—RGB-only observations often fail to encode task-relevant features. Estimation gaps (current observations insufficient for determining violations) and prediction gaps (failures observable but not predictable) create control failures [32].

### Benchmarking Fragmentation

No single benchmark covers world modeling. Different systems are evaluated on video realism (PSNR, SSIM, FVD), physics fidelity, action-conditioned prediction, embodied task success, or long-horizon planning [32]. Benchmark immaturity stems from unstable definitions, fragile long-horizon prediction, heterogeneous architectures, and expensive action-conditioned data collection [32]. Many frontier systems remain proprietary, visual metrics alone are insufficient, physical consistency is hard to measure, and functional testing lacks standardization [32].

Only four benchmarks currently close the loop between prediction generation and executed action, creating persistent methodological gaps [32]. Critical evaluation question remains: do we evaluate physics simulation, embodied utility, or visual appearance—and are these the same thing [7][32]?

### Generalization and Scalability

Generalization across distribution shift and out-of-distribution scenarios remains limited; domain-specific barriers exist in autonomous driving, robotics, and medical imaging [8]. Data bottlenecks require expensive multi-modal, action-annotated sequences [8]. Fundamental framework absence leaves research fragmented without unified definitions [8].

### Interpretability and Safety

Learned latent representations lack mapping to physical variables, limiting utility in classical model-based autonomy and safety verification [12]. Without sufficient physical interpretability, reachability analysis cannot provide guarantees [12]. Safety and alignment risks include adversarial vulnerability, goal misgeneralization, and deceptive alignment [8].

## Trends and open problems

### Scaling Laws Emerging

Foundation models demonstrate scaling properties suggesting continued improvements with data and compute: Genie 2 scales to arbitrary environments; NWM achieves 1B parameters; Sora generates complex video at scale [5][6][27]. However, scaling visual quality does not automatically solve control problems—RoboWM-Bench shows visual realism and executability decouple [7].

### Architectural Convergence

Recent work (Dreamer 4, V-JEPA 2-AC) shows convergence toward hybrid approaches: transformers with world model semantics, JEPA with action conditioning, diffusion with structure-aware training [15][18]. No single family dominates; each retains architectural niches reflecting fundamental physics-appearance-latency tradeoffs [4].

### Physics-Aware Learning Emerging

Increasing integration of physics constraints (symplectic dynamics, conservation laws, residual physics) into learning suggests future systems will jointly optimize neural expressivity with physical consistency [20].

### Evaluation Evolution

RoboWM-Bench, V-JEPA robustness studies, and execution-grounded benchmarking represent shift toward utility-aligned metrics vs. appearance-only evaluation [7][17]. Future benchmarks will likely combine visual quality, physical consistency, and embodied executability as interrelated dimensions [7].

### Open Challenges Blocking Progress

- **Long-horizon coherence**: Error compounding remains structural; models need fundamentally different training objectives for long-horizon planning [32]
- **Physics-appearance decoupling**: Visual realism no longer implies usability; methods must jointly optimize perception and dynamics [7]
- **Representation sufficiency**: Latent spaces must preserve both task-relevant predictability and safety-critical information—current architectures struggle with both [12][18]
- **Evaluation alignment**: Fragmented metrics prevent progress comparison; community needs unified benchmarks spanning visual quality, dynamics accuracy, and embodied utility [32]
- **Safety verification**: No principled approach exists for verifying safety properties in learned world models [12]

These fundamental challenges suggest world models remain in early maturity despite impressive scaling results, with substantial research needed before reliable deployment in safety-critical systems.

## References
[1] Genie 2: A large-scale foundation world model. web. https://deepmind.google/blog/genie-2-a-large-scale-foundation-world-model/ (2024-12-04)
[2] Navigation World Models. arxiv. https://arxiv.org/abs/2412.03572 (2024-12-12)
[3] π₀: A Vision-Language-Action Flow Model for General Robot Control. arxiv. https://arxiv.org/abs/2410.24164v1 (2024-10-24)
[4] PIVOT-R: Primitive-Driven Waypoint-Aware World Model for Robotic Manipulation. web. https://papers.nips.cc/paper_files/paper/2024/file/6164b6e5352c139e9ddc1a98c09e4e4a-Paper-Conference.pdf (2024-11-19)
[5] GenRL: Multimodal-foundation world models for generalization in embodied agents. web. https://proceedings.neurips.cc/paper_files/paper/2024/file/3076133f08b40607d00a8f48f6acd71c-Paper-Conference.pdf (2024-11-19)
[6] M2Diffuser: Diffusion-based Trajectory Optimization for Mobile Manipulation. arxiv. https://arxiv.org/abs/2410.11402 (2024-10-15)
[7] WorldCoder: Model-Based LLM Agent. web. https://papers.nips.cc/paper_files/paper/2024/file/820c61a0cd419163ccbd2c33b268816e-Paper-Conference.pdf (2024-12-10)
[8] Humanoid Locomotion as Next Token Prediction. web. https://papers.nips.cc/paper_files/paper/2024/file/90afd20dc776bc8849c31d61a0763a0b-Paper-Conference.pdf (2024-12-10)
[9] AutoRT: Embodied Foundation Models for Large Scale Orchestration. arxiv. https://arxiv.org/abs/2401.12963 (2024-01-23)
[10] TANGO: Training-free Embodied AI Agents for Open-world Tasks. arxiv. https://arxiv.org/abs/2412.10402 (2024-12-05)
[11] Sora: Video generation models as world simulators. web. https://openai.com/index/video-generation-models-as-world-simulators/ (2024-02-15)
[12] iVideoGPT: Interactive VideoGPTs are Scalable World Models. web. https://proceedings.neurips.cc/paper_files/paper/2024/file/7dbb5bfab324e3b86af9bd0df15498dd-Paper-Conference.pdf (2024-12-10)
[13] AVID: Adapting Video Diffusion Models to World Models. arxiv. https://arxiv.org/abs/2410.12822 (2024-10-28)
[14] Pandora: General World Model with Natural Language Actions and Video States. web. https://arxiv.org/pdf/2406.09455v1 (2024-06-13)
[15] WorldGPT: Empowering LLM as Multimodal World Model. web. https://arxiv.org/abs/2404.18202v1 (2024-04-18)
[16] Safe DreamerV3: Safe Reinforcement Learning with World Models. web. https://arxiv.org/abs/2307.07176 (2023-07-14)
[17] Neural Motion Simulator: Pushing the Limit of World Models in RL. hf-search. https://huggingface.co/papers/2504.07095 (2025-04-09)
[18] Long-Horizon Model-Based Offline RL Without Conservatism. hf-search. https://huggingface.co/papers/2512.04341 (2025-12-04)
[19] WorldCycle: Self-Verifiable RL for Long-Horizon Video World Models. hf-search. https://huggingface.co/papers/2608.04964 (2026-08-05)
[20] World4RL: Diffusion World Models for Policy Refinement. hf-search. https://huggingface.co/papers/2509.19080 (2025-09-23)
[21] ScaleZero: Multi-Task Planning with Efficient World Models. hf-search. https://huggingface.co/papers/2509.07945 (2025-09-09)
[22] GeoWorld: Geometric World Models. hf-search. https://huggingface.co/papers/2602.23058 (2026-02-26)
[23] AgiBot World: Large-Scale Robot Learning Platform. web. https://github.com/OpenDriveLab/AgiBot-World (2024-12-09)
[24] AgiBot World Alpha Dataset. web. https://huggingface.co/datasets/agibot-world/AgiBotWorld-Alpha (2024-12-30)
[25] DROID: A Large-Scale In-The-Wild Robot Manipulation Dataset. web. https://arxiv.org/html/2403.12945 (2024-03-20)
[26] OmniWorld: Multi-Domain Multi-Modal 4D World Modeling Dataset. web. https://github.com/yangzhou24/OmniWorld (2024-12-10)
[27] PhysicalAI WorldModel Synthetic Embodied Robot Scenes. web. https://huggingface.co/datasets/nvidia/PhysicalAI-WorldModel-Synthetic-Embodied-Robot-Scenes (2026-05-01)
[28] Open X-Embodiment: Robotic Learning Datasets. web. https://github.com/google-deepmind/open_x_embodiment (2024-10-01)
[29] 1X World Model Challenge. web. https://github.com/1x-technologies/1xgpt (2024-06-13)
[30] Awesome-WAM: World Action Models Survey. web. https://github.com/OpenMOSS/Awesome-WAM (2024-12-10)
[31] Awesome Robotics Video World Model Papers. web. https://github.com/irom-princeton/awesome-robotics-video-world-model-papers (2024-12-10)
[32] World Knowledge Model for LLM-Based Agent Planning. web. https://papers.nips.cc/paper_files/paper/2024/file/d032263772946dd5026e7f3cd22bce5b-Paper-Conference.pdf (2024-12-10)
[33] Learning Precise Affordances from Egocentric Videos. arxiv. https://arxiv.org/abs/2408.10123 (2024-08-19)
[34] Aligning Cyber Space with Physical World: Comprehensive Survey on Embodied AI. arxiv. https://arxiv.org/abs/2407.06886 (2024-07-09)
