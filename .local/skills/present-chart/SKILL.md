---
name: present-chart
description: Use this skill for presenting data inline as a chart and visualize trends, comparisons, proportions, or multivariate patterns.
---

# Present Chart

Use `presentChart` inside CodeExecution to render a chart inline in the conversation. Include a concise takeaway in your response after presenting it.

Pass data already in the CodeExecution notebook directly into the callback when possible. Variables persist across calls. Data from workspace files can be read and parsed inside a "use impure" function. Map existing variables and loaded data into labels, series, or values and pass it to presentChart without logging the dataset.

Do not present a chart for a single value, a short list, a confirmation, or when prose or a table is clearer.

## Chart Shapes

Bar and line charts require named series and both axis labels:

```js
await presentChart({
  kind: "bar",
  title: "Quarterly revenue",
  labels: ["Q1", "Q2", "Q3"],
  series: [{ name: "Revenue", data: [120, 165, 190] }],
  xAxisLabel: "Quarter",
  yAxisLabel: "USD thousands",
});
```

Radar charts require named series but no axis labels:

```js
await presentChart({
  kind: "radar",
  title: "Product strengths",
  labels: ["Speed", "Quality", "Value"],
  series: [{ name: "Current", data: [8, 9, 7] }],
});
```

Pie, doughnut, and polar-area charts require one value per label:

```js
await presentChart({
  kind: "pie",
  title: "Revenue share",
  labels: ["Product", "Services"],
  values: [70, 30],
});
```

Use 1-50 labels and at most 5 series. Every series or values array must have the same length as `labels`. Pie-family values must be non-negative and include at least one positive value.
