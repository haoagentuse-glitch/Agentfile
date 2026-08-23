# Experiment comparison 的 estimand 與 equivalence 語意

## 問題

Experiment record 目前可保存 baseline、treatment 與數值差。它還不能明確回答四個不同問題。

1. 要估的是哪個量？
2. 用哪個方法估？
3. 這次得到什麼結果與不確定性？
4. 哪個預先指定規則產生哪個判定？

本文件提出最小、跨領域模型。它涵蓋單純 difference、difference-in-differences（DiD），以及 joint cluster bootstrap。它不把臨床試驗術語硬套成完整臨床資料模型。

## 來源發現

### Estimand、estimator、estimate 必須分開

- **VERIFIED — 來源直接結論。** ICH E9(R1) 將 estimand 定義為精確描述研究問題所對應的 treatment effect。其屬性包含 population、treatment conditions、variable、intercurrent-event strategy，以及 population-level summary。[ICH E9(R1) 官方 PDF，A.3.3 與 Glossary](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)
- **VERIFIED — 來源直接結論。** ICH 將 estimator 定義為計算 estimate 的分析方法。Estimate 是 estimator 對資料的數值實現。Main estimator 應與 estimand 對齊。[ICH E9(R1) 官方 PDF，A.5.1 與 Glossary](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)
- **UNVERIFIED — 本專案推論。** 跨領域最小核心可保留 `population`、`conditions`、`outcome`、`summary_measure`。非臨床領域可省略 `intercurrent_event_strategy`。若中途事件會改變問題，則必須填入。
- **UNVERIFIED — 本專案推論。** Decision 不是 estimate 的屬性。它是預先指定規則對 estimate 的輸出。同一 estimate 可供方向、equivalence、non-inferiority 或 gate 規則使用。

### Equivalence 是區間與 margin 的包含關係

- **VERIFIED — 來源直接結論。** ICH E9 指出 equivalence 要用雙側信賴區間。只有完整區間落在上下 equivalence margins 內，才推論 equivalence。這等同 two one-sided tests。[ICH E9 官方 PDF，3.3.2](https://www.fda.gov/media/71336/download)
- **VERIFIED — 來源直接結論。** FDA 的 non-inferiority 指引要求 margin 預先指定，並用信賴區間界限與 margin 比較。Point estimate 與區間寬度也有資訊價值。[FDA Non-Inferiority Clinical Trials，2016](https://www.fda.gov/media/78504/download)
- **VERIFIED — 來源直接結論。** EMA 已採用的指引要求以臨床與統計理由選 margin。事後選 margin 會造成偏差。等價試驗需要上下界。[EMA Choice of a Non-Inferiority Margin，採用版本 PDF](https://www.ema.europa.eu/en/documents/scientific-guideline/guideline-choice-non-inferiority-margin_en.pdf)
- **UNVERIFIED — 本專案推論。** 若 difference 定義為 `treatment - baseline`，且對稱 margin 為 `delta > 0`，則最小規則為：`equivalent = interval.lower > -delta && interval.upper < delta`。若契約選擇含邊界，改用 `>=` 與 `<=`。邊界規則必須在看資料前凍結。
- **UNVERIFIED — 本專案推論。** 必須同時凍結 `confidence_level`、`interval_method`、`margin`、`scale`、`difference_orientation` 與邊界是否包含。只凍結 margin 不足以重現判定。
- **REFUTED — 不採用。** `point_estimate` 落在 margin 內，不足以判 equivalent。來源要求完整區間落在 margin 內。
- **REFUTED — 不採用。** `p > 0.05` 或「未檢出差異」不代表 equivalent。Equivalence 的 null 是效果位於 equivalence range 外。它不是一般差異檢定失敗。[ICH E9 官方 PDF，3.3.2](https://www.fda.gov/media/71336/download)

### `expected_direction` 與 equivalence 分離

- **UNVERIFIED — 本專案推論。** `expected_direction` 只描述 point estimate 的符號預期。它可為 `increase`、`decrease` 或 `no_change`。它不包含可忽略差異的尺度，也不處理不確定性。
- **UNVERIFIED — 本專案推論。** Equivalence 是 decision rule。它需要 interval 與 domain margin。因此 `expected_direction: no_change` 不能映射成 `decision: equivalent`。
- **UNVERIFIED — 本專案推論。** 同一結果可同時是 `direction_matches: true` 與 `equivalent: false`。例如預期 increase，point estimate 為正，但區間越過上 margin。

### Difference、DiD 與 clustered inference

- **VERIFIED — 來源直接結論。** 傳統 DiD 依賴 untreated potential outcomes 的平行趨勢識別假設。Abadie 也展示可用 covariates 調整的 ATT estimand 與 estimator。[Abadie, 2005, *Review of Economic Studies*](https://doi.org/10.1111/0034-6527.00321)
- **VERIFIED — 來源直接結論。** DiD 的序列相關會嚴重低估標準誤。Bertrand、Duflo、Mullainathan 建議保留群內跨期共變異，或使用適合設計的替代推論。[Bertrand, Duflo, Mullainathan, 2004；NBER 原始版本與正式出版資訊](https://www.nber.org/papers/w8841)
- **VERIFIED — 來源直接結論。** Cluster bootstrap 的有效性取決於資料模型與 resampling scheme。Field 與 Welsh 證明，在其 one-way clustered data 設定下，cluster bootstrap 對 transformation 與 random-effect models 的 variance estimation 一致。[Field and Welsh, 2007](https://doi.org/10.1111/j.1467-9868.2007.00593.x)
- **VERIFIED — 來源直接結論。** 當 cluster 數少時，一般 cluster-robust 常態近似可能不佳。Cameron、Gelbach、Miller 研究 bootstrap refinements，並要求 bootstrap 與 clustered error 結構相容。[Cameron, Gelbach, Miller, 2008；NBER 原始論文](https://www.nber.org/papers/t0344)
- **UNVERIFIED — 本專案推論。** 若 difference、DiD 與其他 components 共享 clusters，每次 replicate 必須只抽一次 cluster index，並用同一抽樣同時計算所有 components。這裡的 `joint` 是共同 resampling schedule。它保留 component 間 bootstrap dependence。它不是新的 estimand。

## 最小資料模型建議

四層模型如下。`estimand` 與 `estimator` 應在看結果前凍結。`estimate` 是執行輸出。`decision` 引用凍結規則與 estimate。

```yaml
estimand:
  id: effect.primary
  population: "可檢查的資料或樣本範圍"
  conditions:
    baseline: "A"
    treatment: "B"
  outcome:
    metric_ref: recall_at_10
    scale: raw                    # raw | log | ratio | other named scale
  summary_measure:
    type: difference              # difference | difference_in_differences
    orientation: treatment_minus_baseline
  intercurrent_event_strategy: null  # 有中途事件時才必填

estimator:
  id: estimator.primary.v1
  estimand_ref: effect.primary
  method:
    name: arithmetic_difference
    version: "1"
    reference_url: null
    parameters: {}
  uncertainty:
    name: joint_cluster_bootstrap
    confidence_level: 0.95
    interval_method: percentile
    resampling_unit: project_id
    strata: []
    replicates: 10000
    seed: 1729
    method_reference_url: "https://doi.org/10.1111/j.1467-9868.2007.00593.x"

estimate:
  estimand_ref: effect.primary
  estimator_ref: estimator.primary.v1
  point_estimate: 0.018
  interval:
    lower: -0.006
    upper: 0.039
    confidence_level: 0.95
    method: percentile
  sample_size:
    observations: 840
    clusters: 42
    by_condition:
      baseline: 420
      treatment: 420
  components:
    - id: baseline_mean
      role: subtrahend_component
      point_estimate: 0.731
      interval: {lower: 0.710, upper: 0.751, confidence_level: 0.95, method: percentile}
      sample_size: {observations: 420, clusters: 42}
    - id: treatment_mean
      role: minuend_component
      point_estimate: 0.749
      interval: {lower: 0.729, upper: 0.770, confidence_level: 0.95, method: percentile}
      sample_size: {observations: 420, clusters: 42}

decision:
  estimate_ref: effect.primary
  rule:
    type: equivalence
    lower_margin: -0.05
    upper_margin: 0.05
    scale: raw
    interval_confidence_level: 0.95
    interval_method: percentile
    boundary: exclusive
    frozen_at: "2026-08-23T00:00:00Z"
    rule_ref: contract-id-or-content-hash
  equivalent: true
  reason_codes: [interval_inside_margin]
```

### Difference

- **UNVERIFIED — 本專案推論。** 保存 `baseline` 與 `treatment` component estimates。保存 `point_estimate = treatment - baseline`。不要只保存三個數而省略 orientation。
- **UNVERIFIED — 本專案推論。** 若輸入為 paired 或 clustered data，`sample_size` 要同時保存 observations 與獨立 resampling units。單一整數會隱藏有效樣本單位。

### Difference-in-differences

DiD 至少保存四個 cell estimates。衍生 components 也要保存。

```yaml
summary_measure:
  type: difference_in_differences
  formula: "(treatment.post - treatment.pre) - (control.post - control.pre)"
estimate:
  point_estimate: 0.031
  interval: {lower: 0.008, upper: 0.054, confidence_level: 0.95, method: percentile}
  sample_size: {observations: 1600, clusters: 40}
  components:
    - {id: control_pre, point_estimate: 0.61, sample_size: {observations: 400, clusters: 20}}
    - {id: control_post, point_estimate: 0.63, sample_size: {observations: 400, clusters: 20}}
    - {id: treatment_pre, point_estimate: 0.60, sample_size: {observations: 400, clusters: 20}}
    - {id: treatment_post, point_estimate: 0.65, sample_size: {observations: 400, clusters: 20}}
    - {id: control_change, point_estimate: 0.02}
    - {id: treatment_change, point_estimate: 0.05}
```

- **UNVERIFIED — 本專案推論。** `formula` 或結構化 signs 必須固定。只寫 `type: difference_in_differences` 不能排除反向相減。
- **UNVERIFIED — 本專案推論。** Component estimates 是可稽核分解。它們不是獨立 confirmatory decisions。若要對 component 下判定，要建立另一個 estimand 與 rule。

### Joint cluster bootstrap

- **UNVERIFIED — 本專案推論。** `method_reference_url` 指向方法家族。`name`、版本、參數與程式 provenance 指向本次具體實作。只存 DOI 不能重算。
- **UNVERIFIED — 本專案推論。** 每個 component 與最終 contrast 都應由同一組 replicate 計算。持久化 point estimates、intervals 與 sample sizes。可選擇保存 bootstrap covariance matrix 或 replicate artifact 的 content hash。
- **UNVERIFIED — 本專案推論。** 最小 provenance 還要有 `resampling_unit`、`strata`、`replicates`、`seed`、interval method、confidence level、失敗 replicate 數，以及 software/version 或 code hash。
- **UNVERIFIED — 本專案推論。** Cluster 數是 inference 的主要 sample-size 訊息。Observations 數仍要保存，但不可替代 clusters 數。

## 失敗條件

以下任一條成立時，不得輸出 `equivalent: true`。

1. Estimand、difference orientation、scale 或 outcome 未凍結。
2. Margin 在看過 estimate 或 interval 後才選定。
3. Interval level、interval method 或邊界規則未凍結。
4. Interval 任一端越過 margin。Interval 缺失也視為不可判定。
5. Margin 與 interval 不在同一 scale。
6. Estimator 與 estimand 不對齊。例如估 ratio，卻對 raw difference margin 判定。
7. Clustered data 以 row bootstrap 打散 cluster dependence，卻宣稱是 cluster bootstrap。
8. Joint components 使用不同 bootstrap draws，卻宣稱保留 joint dependence。
9. DiD 未記錄四個 cells、相減方向，或識別假設的適用範圍。
10. Cluster 數太少，但方法仍依賴 large-cluster approximation，且沒有警告或預先指定的替代方法。

預登記的改判證據如下。

- 若官方或原始方法來源證明特定領域可用不同 interval 或不對稱 margin，模型保留該方法與上下 margin，不強制對稱。
- 若實作無法從單一 joint resampling schedule 重建所有 components，則不得使用 `joint_cluster_bootstrap` 名稱。
- 若使用者只需要描述性數值，不需要不確定性判定，可省略 decision。但不可把描述性結果標成 equivalent。

## 明確不採用項目

1. 不把 `expected_direction: no_change` 當 equivalence。
2. 不用 point estimate 單獨判 equivalence。
3. 不用傳統差異檢定的 `p > alpha` 判 equivalence。
4. 不用 `absolute_diff <= margin` 取代區間規則。
5. 不把 estimand、estimator、estimate 合成一個無版本 `method` 字串。
6. 不只保存最終 DiD。必須保存四個 cell estimates 與兩個 change components。
7. 不只保存 observations。Clustered inference 必須保存 cluster 數。
8. 不保存全部 bootstrap replicates 作為核心 schema 必填欄位。大型 replicates 可放 artifact。核心 record 保存 hash、摘要與重算 provenance。
9. 不宣稱所有 cluster bootstrap 都有效。有效性依資料模型、cluster 數與 resampling scheme 而定。
10. 不在本最小模型加入完整臨床試驗 intercurrent-event taxonomy、multiplicity graph、Bayesian posterior 或 causal DAG。出現真實需求時再擴充。
