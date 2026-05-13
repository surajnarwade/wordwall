{{/*
Expand the name, falling back to the Helm release name.
*/}}
{{- define "wordwall.name" -}}
{{- default .Release.Name .Values.name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "wordwall.labels" -}}
app.kubernetes.io/name: {{ include "wordwall.name" . }}
app.kubernetes.io/instance: {{ required "values.backstage.component is required" .Values.backstage.component }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
tags.datadoghq.com/service: {{ required "values.backstage.component is required" .Values.backstage.component }}
{{- end }}

{{- define "wordwall.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wordwall.name" . }}
app.kubernetes.io/instance: {{ required "values.backstage.component is required" .Values.backstage.component }}
{{- end }}
