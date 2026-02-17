import { Brain, TrendingUp, AlertCircle } from "lucide-react";
import { useState } from "react";
import type { ConflictPrediction } from "@/lib/graph/graph-utils";

export interface ConflictPredictionPanelProps {
  predictions: ConflictPrediction[];
  modelVersion?: string;
  confidenceThreshold?: number;
  onPredictionClick?: (prediction: ConflictPrediction) => void;
  className?: string;
}

export default function ConflictPredictionPanel({
  predictions,
  modelVersion,
  confidenceThreshold,
  onPredictionClick,
  className = "",
}: ConflictPredictionPanelProps) {
  const [minProbability, setMinProbability] = useState(0.5);

  const filteredPredictions = predictions.filter(
    (p) => p.conflict_probability >= minProbability
  );

  const getProbabilityColor = (prob: number): string => {
    if (prob >= 0.75) return "text-red-600 bg-red-50";
    if (prob >= 0.5) return "text-orange-600 bg-orange-50";
    return "text-yellow-600 bg-yellow-50";
  };

  const getProbabilityLabel = (prob: number): string => {
    if (prob >= 0.75) return "Très élevée";
    if (prob >= 0.5) return "Élevée";
    if (prob >= 0.25) return "Modérée";
    return "Faible";
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-md border border-neutral-200 p-4 ${className}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Brain className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-neutral-900">
              Prédictions de conflits
            </h3>
          </div>
          <p className="text-xs text-neutral-500">
            Détection proactive par IA • {filteredPredictions.length} prédiction
            {filteredPredictions.length > 1 ? "s" : ""}
          </p>
        </div>
        {modelVersion && (
          <div className="text-xs text-neutral-400">v{modelVersion}</div>
        )}
      </div>

      {/* Probability filter */}
      <div className="mb-4">
        <label className="text-xs font-medium text-neutral-700 mb-2 block">
          Probabilité minimale: {Math.round(minProbability * 100)}%
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={minProbability}
          onChange={(e) => setMinProbability(parseFloat(e.target.value))}
          className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
        />
      </div>

      {/* Predictions list */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {filteredPredictions.length === 0 ? (
          <div className="text-center py-8 text-neutral-500 text-sm">
            Aucune prédiction au-dessus du seuil sélectionné
          </div>
        ) : (
          filteredPredictions.map((prediction, index) => (
            <div
              key={index}
              className="border border-neutral-200 rounded-lg p-3 hover:border-purple-300 hover:shadow-sm transition-all cursor-pointer"
              onClick={() => onPredictionClick?.(prediction)}
            >
              {/* Entities */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-neutral-900">
                    {prediction.entity_names[0]}
                  </span>
                  <TrendingUp className="w-3 h-3 text-neutral-400" />
                  <span className="text-sm font-medium text-neutral-900">
                    {prediction.entity_names[1]}
                  </span>
                </div>
              </div>

              {/* Probability */}
              <div className="flex items-center gap-2 mb-2">
                <div
                  className={`px-2 py-1 rounded text-xs font-medium ${getProbabilityColor(prediction.conflict_probability)}`}
                >
                  {Math.round(prediction.conflict_probability * 100)}%
                </div>
                <span className="text-xs text-neutral-600">
                  {getProbabilityLabel(prediction.conflict_probability)}
                </span>
              </div>

              {/* Risk factors */}
              {prediction.risk_factors.length > 0 && (
                <div className="mb-2">
                  <p className="text-xs font-medium text-neutral-600 mb-1">
                    Facteurs de risque:
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {prediction.risk_factors.map((factor, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 bg-red-50 text-red-700 rounded text-xs"
                      >
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommended actions */}
              {prediction.recommended_actions.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-neutral-600 mb-1">
                    Actions recommandées:
                  </p>
                  <ul className="space-y-1">
                    {prediction.recommended_actions
                      .slice(0, 2)
                      .map((action, idx) => (
                        <li
                          key={idx}
                          className="text-xs text-neutral-700 flex items-start gap-1"
                        >
                          <AlertCircle className="w-3 h-3 text-purple-600 flex-shrink-0 mt-0.5" />
                          <span>{action}</span>
                        </li>
                      ))}
                  </ul>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Disclaimer */}
      {confidenceThreshold && (
        <div className="mt-4 pt-3 border-t border-neutral-200">
          <p className="text-xs text-neutral-500 text-center">
            Seuil de confiance: {Math.round(confidenceThreshold * 100)}%
          </p>
        </div>
      )}
    </div>
  );
}
