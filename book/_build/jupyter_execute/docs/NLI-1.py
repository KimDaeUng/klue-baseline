#!/usr/bin/env python
# coding: utf-8

# # Weight & Biase 을 활용한 Tokenizer 별 성능 비교 

# - Task : KLUE-NLI
# - 담당자 : [권지현](https://github.com/Jihyun22) 님
# - 최종 수정일 : 21-08-18
# - 본 자료는 가짜연구소 3기 KLUE 로 모델 평가하기 크루 활동으로 작성됨

# # 01 init
# KLUE-NLI task 를 다룰 때 필요한 기초적인 환경 설정 방법에 대해 설명합니다.
# 
# ---

# ## Install packages
# 
# 필요한 패키지를 설치합니다. 본 노트북에서는 3개의 패키지를 새로 설치해야 합니다.
# 1. transformers : hugging face(관련 페이지 [링크](https://github.com/huggingface/transformers#installation)) 에서 포팅된 데이터, 모델 등을 불러오기 위해 사용합니다. 
# 2. `datasets` : hugging face 의 datasets 라이브러리(관련 페이지 [링크](https://github.com/huggingface/datasets)) 중 `load_dataset` 매서드를 사용하면 쉽게 데이터를 다운로드 받을 수 있습니다.
# 3. wandb : 모델 학습 시 log 를 관리하기 위해 "Weight and Biases"(관련 페이지 [링크](https://wandb.ai/site)) 를 사용합니다.

# In[ ]:


get_ipython().system('pip install transformers datasets wandb')


# 본 노트북에서는 `transformers` 4.9.2 버전을 사용합니다.

# In[ ]:


import transformers
print(transformers.__version__) # 4.9.2 버전


# ## Variable setting
# 
# 다음으로 기본적인 변수를 선언합니다.
# 1. task : task 의 이름을 str 형태로 저장하여 task 을 구분합니다.
# 2. model_checkpoint : model 을 다운받을 hugging face 상 경로를 의미합니다. klue 데이터의 bert 기반 pretrained model 은 "klue/bert-base"에 업로드되어 있습니다.
# 3. batch_size : batch_size 는 128 로 설정하였습니다.

# In[ ]:


# task 관련 변수 선언
task = "nli"
model_checkpoint = "klue/bert-base"
batch_size = 128 # 64


# ## Access huggingface 
# 
# huggingface에 접근하기 위해서는 로그인이 필요합니다. 가입이 되어 있지 않은 경우 [링크](https://huggingface.co/welcome) 에서 관련 작업을 진행할 수 있습니다.
# 
# 다음 셀에서 Username 와 Password 를 입력합니다.

# In[ ]:


get_ipython().system('huggingface-cli login')


# 로그인이 완료되었다면, hf-lfs 를 설치한 후 e-mail, name 을 설정합니다.

# In[ ]:


get_ipython().system('pip install hf-lfs')
get_ipython().system('git config --global user.email "jih020202@gmail.com"')
get_ipython().system('git config --global user.name "Jihyun22"')


# 이제 hugging face 를 사용할 수 있습니다. 다음 단계에서는 hugging face 의 라이브러리를 사용하여 데이터 셋을 다운로드 받는 방법에 대해 다루겠습니다.
# 
# ----

# # 02 Data Loading
# KLUE-NLI task 중 hugging face 에서 Data set 을 가져오는 방법에 대해 다룹니다.
# 
# ---

# ## Data Download
# hugging face 의 `Datasets` 라이브러리를 사용하여 데이터를 불러옵니다. load_dataset 매서드를 이용합니다.

# In[ ]:


from datasets import load_dataset
dataset = load_dataset('klue', task) # klue 의 task=nil 을 load
dataset # dataset 구조 확인


# ## Data view
# 
# dataset 는 train 셋과 validation 으로 구성되어 있습니다.
# 
# 각각의 set의 구조를 데이터 샘플을 통해 살펴보겠습니다.

# In[ ]:


dataset['train'][0]


# klue 의 nli task dataset 구조는 다음과 같습니다. 자세한 내용은 klue 공식 페이지 [링크](https://github.com/KLUE-benchmark/KLUE/wiki/KLUE-NLI-dataset-description)를 참조바랍니다.
#   1. 'guid' : index, 고유 식별자
#   2. 'hypothesis': 가설 문장
#   3. 'label': 라벨 (gold label 을 의미)
#   4. 'premise': 전제 문장
#   5. 'source': 문장 출처
# 
# 각 column 구성을 임의의 샘플을 추출하여 살펴보겠습니다.

# In[ ]:


import datasets
import random
import pandas as pd
from IPython.display import display, HTML

def show_random_elements(dataset, num_examples=10):
    assert num_examples <= len(dataset), "Can't pick more elements than there are in the dataset."
    picks = []
    for _ in range(num_examples):
        pick = random.randint(0, len(dataset)-1)
        while pick in picks:
            pick = random.randint(0, len(dataset)-1)
        picks.append(pick)
    
    df = pd.DataFrame(dataset[picks])
    for column, typ in dataset.features.items():
        if isinstance(typ, datasets.ClassLabel):
            df[column] = df[column].transform(lambda i: typ.names[i])
    display(HTML(df.to_html()))

show_random_elements(dataset["train"])


# NLI task 의 목적은 `premise`와 `hypothesis`문장 간 관계를 판단하는 것 입니다. 따라서 input 값은 `premise`, `hypothesis` 이며, label 이 y 값으로 사용됩니다.
# 
# 다음은 데이터 전처리 과정을 살펴보겠습니다.
# 
# ----

# # 03 Data Processing
# KLUE-NLI task 중 Tokenizer를 사용하여 데이터를 인코딩한 후 전처리하는 과정을 설명합니다.
# 
# ---

# ## Tokenizer load
# 
# 전처리를 위해 Transformers Tokenizer 로 데이터를 인코딩하는 과정이 필요합니다. Transformers Tokenizer는 모델의 입력 텍스트를 토큰으로 변환하여 모델이 입력받는 포맷으로 만들어줍니다.
# 
# 또한 사용하고자 하는 모델과 관련된 Tokenizer 을 얻을 수 있습니다. 따라서 본 노트북에서는 KLUE 의 bert base pretrianed model에서 사용된 Tokenizer 을 활용하여 포팅된 모델을 사용하여 데이터를 인코딩 하겠습니다.

# In[ ]:


import torch
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(model_checkpoint, use_fast=True)


# ## Data encoding
# 
# Tokenizer 는 문장 또는 문장 쌍을 입력하여 데이터에 대한 토크나이징을 수행할 수 있습니다.
# 
# NLI task 에서는 `premise`, `hypothesis` 2개의 input 값이 필요합니다. tokenizer의 입력값을 고려하여 전처리를 수행할 함수를 정의하겠습니다. 

# In[ ]:


max_length = 512 
def preprocess_function(examples):
    return tokenizer(examples['hypothesis'], examples['premise'],
                     truncation=True, max_length=max_length, padding=True)


# 이때 `truncation=True` 을 통해 token 의 length 길이를 설정할 수 있습니다. 기본값 `max_length = 512` 은 공식 페이지 [링크](https://github.com/KLUE-benchmark/KLUE-baseline)를 참고하였습니다.
# 
# `map` 매서드를 사용하여 전처리 함수를 전체 데이터셋에 적용할 수 있습니다. 

# In[ ]:


encoded_dataset = dataset.map(preprocess_function, batched=True)


# `batched=True` 으로 데이터를 배치로 묶어 전체 dataset에 대해 인코딩을 완료했습니다. tokenizer 은 멀티 쓰레딩을 사용하여 텍스트 데이터를 배치 형태로 빠르게 처리할 수 있습니다.
# 
# 다음으로 hugging face 에 포팅된 Pretrained model 을 load 하여 fine tuning 하는 방법에 대해 다루겠습니다.
# 
# ---

# # 04 Fine tuning
# 
# KLUE-NLI task 중 Pretrained model 을 사용하여 fine-tuning 하는 방법에 대해 다루겠습니다.
# 
# 
# ---

# ## Model load
# 
# Pretrained model을 다운 받아 fine tuning 을 진행할 수 있습니다. NLI task는 분류와 관련한 task 이므로 , `AutoModelForSequenceClassification` 클래스를 사용하겠습니다.
# 
# 이때, label 개수에 대한 설정이 필요합니다.

# In[ ]:


dataset['train'].features['label'] # num_classes=3 


# NLI task 는 총 3개의 label 로 구성되어 있습니다.
# 
# 다음으로 모델을 불러오겠습니다. KLUE base 모델은 hugging face model hub (관련 사이트 [링크](https://huggingface.co/models)) 에 포팅되어 있으므로 model_checkpoint 경로를 정의하여 불러올 수 있습니다(`model_checkpoint = klue/bert-base` 로 사전 정의됨).
# 

# In[ ]:


from transformers import AutoModelForSequenceClassification, TrainingArguments, Trainer
num_labels = 3 # label 개수는 task 마다 달라질 수 있음
model = AutoModelForSequenceClassification.from_pretrained(model_checkpoint,
                                                           num_labels=num_labels)


# ## Parameter setting
# HuggingFace 에서는 `Trainer` 객체를 사용하여 학습을 진행합니다. 이때, `Trainer` 객체는 모델 학습을 위해 설정해야 하는 값이 들어있는 클래스인 `TrainingArgument`를 입력받아야 합니다.
# 
# 이번 단계에서는 모델 학습을 위한 trainer 객체를 정의하는 방법에 대해 다루겠습니다.
# 

# In[ ]:


import os

model_name = model_checkpoint.split("/")[-1]
output_dir = os.path.join("test-klue", "nli") # task 별로 바꿔줄 것
logging_dir = os.path.join(output_dir, 'logs')

args = TrainingArguments(
    # checkpoint, 모델의 checkpoint 가 저장되는 위치
    output_dir=output_dir, 
    # overwrite_output_dir=True,

    # Model Save & Load
    save_strategy = "epoch", # 'steps'
    load_best_model_at_end=True,
    # save_steps = 500,

    # Dataset, epoch 와 batch_size 선언
    num_train_epochs=5,
    per_device_train_batch_size=batch_size,
    per_device_eval_batch_size=batch_size,
    
    # Optimizer
    learning_rate=2e-5, # 5e-5
    weight_decay=0.01,  # 0
    # warmup_steps=200,

    # Resularization
    # max_grad_norm = 1.0,
    # label_smoothing_factor=0.1,

    # Evaluation, 평가지표
    metric_for_best_model='accuracy', # task 별 평가지표 변경
    evaluation_strategy = "epoch",

    # HuggingFace Hub Upload, 모델 포팅읠 위한 인자
    push_to_hub=True,
    push_to_hub_model_id=f"{model_name}-finetuned-{task}",

    # Logging, log 기록을 살펴볼 위치, 본 노트북에서는 wandb 를 이용함
    logging_dir=logging_dir,
    report_to='wandb',

    # Randomness, 재현성을 위한 rs 설정
    seed=42,
)


# `TrainingArguments` 의 여러 인자 중 필수 인자는 `output_dir` 으로 모델의 checkpoint 가 저장되는 경로를 의미합니다.
# 또한 task 별로 metric 지정이 필요합니다. NLI task 는 accuracy 를 평가지표로 사용합니다.
# 
# 다음으로 trainer 객체를 정의하겠습니다. 우선 metric 설정이 필요합니다. datasets 라이브러리에서 제공하는 Evaluation metric의 리스트를 확인하겠습니다.

# In[ ]:


# metric list 확인
from datasets import list_metrics, load_metric
metrics_list = list_metrics()
len(metrics_list)
print(', '.join(metric for metric in metrics_list))


# 이 중, NLI 에서는 `accuracy` 를 사용합니다. 해당 평가지표를 고려하여 metric 계산을 위한 함수를 정의하겠습니다.

# In[ ]:


metric_name = "accuracy"
metric_accuracy = load_metric(metric_name) # metric 불러오기

# metric 계산을 위한 함수
def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = predictions[:, 0]
    ac = metric_accuracy.compute(predictions=predictions,
                                  references=labels)
    return ac


# 마지막으로 `trainer` 객체를 정의하겠습니다.

# In[ ]:


trainer = Trainer(
    model,
    args,
    train_dataset=encoded_dataset["train"],
    eval_dataset=encoded_dataset['validation'],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)


# 앞에서 tokenizer를 사용해 전처리를 했음에도 `Trainer`의 인자로 다시 넣는 이유는 패딩을 적용해서 입력 샘플들을 동일한 길이로 만들기 위해 사용하기 때문입니다. 모델에 따라 패딩에 대한 기본 설정이 다르기 때문에(왼쪽 패딩, 오른쪽 패딩, 또는 패딩 인덱스 번호 설정 등) Trainer는 이와 관련된 작업을 수행할 수 있은 tokenizer 객체를 사용합니다.
# 
# Fine-tuning 을 위한 준비가 완료되었습니다. 다음 단계에서는 fine-tuning 과 training log 를 관리하는 법에 대해 다루겠습니다.
# 
# ---

# # 05 Training
# 
# KLUE-NLI task 중 training log 를 관리하는 방법과 hyperparameter search 을 통해 모델 성능을 높이는 방법에 대해 다루겠습니다.
# 
# 
# ---

# ## Weights & Biases setting
# 
# huggingface 는 모델 학습 로그를 기록할 때 Tensorboard 또는 Weights & Biases를 사용할 수 있습니다. 본 노트북에서는 Weights & Biases를 사용하겠습니다.
# 
# 우선 wandb id 를 생성하여 실험 관리를 위한 세팅을 진행합니다. wandb id 가 있는 경우, https://wandb.ai/authorize 에서 code 를 다음 셀에 입력하면 자동으로 연동됩니다.

# In[ ]:


import wandb
wandb.login()
id = wandb.util.generate_id() # id 생성
print(id)


# 생성된 id 를 붙여넣으면 wandb 를 사용할 수 있습니다.

# In[ ]:


wandb.init(project='klue', #  실험기록을 관리할 프로젝트 이름. 없을 시 입력받은 이름으로 생성
           entity='Jihyun22', # 사용자명 또는 팀 이름
           id='34hc23p1', # 실험에 부여된 고유 아이디
           name='nli', # 실험에 부여한 이름
            )


# ## Training
# 
# 이제 `Trainer` 객체를 사용하여 학습을 진행할 수 있습니다.

# In[ ]:


trainer.train() # 학습 시작


# 학습이 완료된 후, evaluate 메서드를 사용하여 Trainer가 best 모델로 불러온 모델의 성능을 확인해볼 수 있습니다.

# In[ ]:


trainer.evaluate() # 성능 확인


# 학습이 끝나면 wandb 역시 종료합니다.

# In[ ]:


wandb.finish() # wandbe 종료


# push_to_hub() 메서드를 사용하여 tokenizer를 비롯한 모델을 Hub에 업로드할 수 있습니다.

# In[ ]:


trainer.push_to_hub()


# 업로드한 모델을 Hub-user-name/사용자가 지정한 이름으로 바로 다운로드하여 사용할 수 있습니다.

# In[ ]:


from transformers import AutoModelForSequenceClassification
# {HuggingFace Model Hub 사용자 아이디}/{push_to_hub_model_id에서 설정한 값}
model = AutoModelForSequenceClassification.from_pretrained('Jihyun22/bert-base-finetuned-nil', num_labels=num_labels)


# ## Hyperparameter search
# 
# 위 모델의 성능을 높이기 위해 Hyperparameter search 방법을 사용할 수 있습니다. `Trainer` 는  optuna 또는 Ray Tune를 이용한 hyperparameter search를 지원합니다.
# 
# 우선 관련 라이브러리를 설치하겠습니다.

# In[ ]:


get_ipython().system('pip install optuna')
get_ipython().system('pip install ray[tune]')


# hyperparameter search 동안 `Trainer`는 학습을 여러 번 수행합니다. 따라서 모델이 매 학습마다 다시 초기화 될 수 있도록 모델이 함수에 의해 정의되도록 합니다.
# 
# 모델 초기화 함수를 정의하겠습니다.

# In[ ]:


def model_init():
    return AutoModelForSequenceClassification.from_pretrained(model_checkpoint, num_labels=num_labels)


# 모델 초기화 단계를 포함한 `Trainer`를 새롭게 정의하겠습니다. 이때, TrainingArguments 은 위에서 선언한 내용을 그대로 사용합니다.
# 
# 또한 hyperparameter search 과정에서 학습 시 시간이 오래 소요될 수 있습니다. 이 경우, `.shard(index=1, num_shards=10) ` 을 통해 일부 데이터 셋에 대한 hyperparameter 를 탐색할 수 있습니다.
# 
# num_shards 의 수에 따라 1/10, 1/5 데이터 만을 사용할 수 있습니다. 본 노트북에서는 1/5 데이터셋만 사용하여 hyperparameter 를 탐색하겠습니다. 
# 
# 물론, 탐색된 hyperparameter 는 전체 데이터에 대해 학습할 때 적용되어 최종 모델을 정상적으로 학습시킬 수 있습니다.

# In[ ]:


trainer_hps = Trainer(
    model_init=model_init,
    args=args,
    train_dataset=encoded_dataset["train"].shard(index=1, num_shards=5), # 일부 데이터셋만 선택하여 진행 가능
    eval_dataset=encoded_dataset['validation'],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)


# `Trainer`정의가 완료되었다면, log 기록을 위해 wandb 를 다시 설정합니다. 위의 과정과 동일합니다.

# In[ ]:


wandb.init()
wandb.login()
id = wandb.util.generate_id()
print(id)


# wandb 에서 project 이름을 변경하여 wandb 를 초기화합니다.

# In[ ]:


wandb.init(project='klue-nli-hps',
           entity='Jihyun22',
           id='3dbjx4nx'
           )


# 이제 `hyperparameter_search` 매서드를 사용하여 탐색 및 학습을 진행할 수 있습니다.
# `hyperparameter_search` 메서드는 BestRun 객체를 반환합니다. 이 객체는 최대화된 objective의 값(평가지표의 값, 본 task 에서는 accuracy)과 이때 선택된 hyperparameter를 포함합니다.

# In[ ]:


best_run = trainer_hps.hyperparameter_search(n_trials=5, direction="maximize")


# 최종 best_run 에서 탐색된 hyperparameter 값은 다음과 같습니다. 정확도 역시 기존 training 결과에 비해 상승한 결과를 확인할 수 있습니다.
# 

# In[ ]:


best_run


# 해당 모델도 hub 에 업로드하겠습니다.

# In[ ]:


# Hub에 업로드
trainer_hps.push_to_hub()


# 지금까지 fine-tuning 시 training 과정과 log 관리, hyperparameter search 에 대해 살펴보았습니다.
# 
# 본 실험의 결과는 링크 에서 확인할 수 있으며, 다음 부록에서는 hyperparameter search 시 optuna, ray custom 방법에 대해 소개하겠습니다.
# 
# 다음 단계는 모델 저장 및 제출에 대해 살펴보겠습니다.
# 
# ---

# # 06 Submission
# 
# (추후 추가 예정).
# 
# 
# ---

# In[ ]:


trainer_hps.save('/test-klue/nil/model_hps.h5')


# In[ ]:


import sys
# if you have many scripts add this line before you import them
sys.path.append('/test-klue/nil/') 

actor = build_actor()
actor.load_weights('/test-klue/nil/model_hps.actor.h5')

def agent(obs):
    action = actor.predict(...)
    return [action]


# In[ ]:


get_ipython().system(' tar -czvf submission.tar.gz main.py model.actor.h5')


# ---

# # 07 Reference
# 
# - Text Classification on GLUE
# 
# 
# ---

# In[ ]:




