---
license: apache-2.0
task_categories:
- question-answering
language:
- en
tags:
- industry
pretty_name: FailureSensorIQ
size_categories:
- 1K<n<10K
configs:
- config_name: single_true_multi_choice_qa
  data_files:
  - split: train
    path: failuresensoriq_standard/all.jsonl
  default: true
- config_name: multi_true_multi_choice_qa
  data_files:
  - split: train
    path: failuresensoriq_standard/all_multi_answers.jsonl
dataset_info:
  features:
  - name: subject
    dtype: string
  - name: id
    dtype: int32
  - name: question
    dtype: string
  - name: options
    sequence:
      dtype: string
  - name: option_ids
    sequence:
      dtype: string
  - name: question_first
    dtype: bool
  - name: correct
    sequence:
      dtype: bool
  - name: text_type
    dtype: string
  - name: asset_name
    dtype: string
  - name: relevancy
    dtype: string
  - name: question_type
    dtype: string
---

# FailureSensorIQ Dataset

FailureSensorIQ is a Multi-Choice QA (MCQA) dataset that explores the relationships between sensors and failure modes for 10 industrial assets.

|[**Github**](https://github.com/IBM/FailureSensorIQ) | [**🏆Leaderboard**](https://huggingface.co/spaces/cc4718/FailureSensorIQ) | [**📖Paper**](https://arxiv.org/abs/2506.03278) |

## Dataset Summary
FailureSensorIQ is a Multi-Choice QA (MCQA) dataset that explores the relationships between sensors and failure modes for 10 industrial assets. By only leveraging the information found in ISO documents, we developed a data generation pipeline that creates questions in two types: (i) FailureMode2Sensor and (ii) Sensor2FailureMode. Additionally, we designed questions in a selection (select the relevant ones) vs. elimination (eliminate the irrelevant ones) format. 

FailureSensorIQ dataset consists of 8,296 questions across 10 assets, with 2,667 single-true multi-choice questions and 5,629 multi-true multi-choice questions. The following is the list of assets with count within 2,667 single-true multi-choice questions:

| Asset                       | Count |
|-----------------------------|-------|
| Electric Motor              | 234   |
| Steam Turbine               | 171   |
| Aero Gas Turbine            | 336   |
| Industrial Gas Turbine      | 240   |
| Pump                        | 152   |
| Compressor                  | 220   |
| Reciprocating IC Engine     | 336   |
| Electric Generator          | 234   |
| Fan                         | 200   |
| Power Transformer           | 544   |

Please find more statistics of the dataset and the dataset construction process from our [Github](https://github.com/IBM/FailureSensorIQ) and [Paper](https://arxiv.org/abs/2506.03278).

## Load the Dataset
To load 2,667 single-true multi-choice QA,

```python
from datasets import load_dataset

# Login using e.g. `huggingface-cli login` to access this dataset
ds = load_dataset("ibm-research/FailureSensorIQ", "single_true_multi_choice_qa")
```

To load  5,629 multi-true multi-choice QA,
```python
from datasets import load_dataset

# Login using e.g. `huggingface-cli login` to access this dataset
ds = load_dataset("ibm-research/FailureSensorIQ", "multi_true_multi_choice_qa")
```

## Leaderboard
We have benchmarked both open-source LLMs and frontier LLMs on FailureSensorIQ. Furthermore, we have conducted thoroughout Perturbation–Uncertainty–Complexity analysis for deeper insights of each LLMs. For the most updated leaderboard, please refer to our [Leaderboard](https://huggingface.co/spaces/cc4718/FailureSensorIQ). You can submit the evaluation there. 

If you want to reproduce our results, please check out our [Github](https://github.com/IBM/FailureSensorIQ) for the evaluation scripts. We documented all the steps you should take to run the evaluation.

## Cite this Dataset
If you use our dataset in your paper, please cite our dataset by
```
@misc{constantinides2025failuresensoriqmultichoiceqadataset,
      title={FailureSensorIQ: A Multi-Choice QA Dataset for Understanding Sensor Relationships and Failure Modes}, 
      author={Christodoulos Constantinides and Dhaval Patel and Shuxin Lin and Claudio Guerrero and Sunil Dagajirao Patil and Jayant Kalagnanam},
      year={2025},
      eprint={2506.03278},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2506.03278}, 
}
```