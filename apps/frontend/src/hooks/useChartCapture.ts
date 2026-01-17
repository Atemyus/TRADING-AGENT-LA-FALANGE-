"use client";

import { useCallback, useRef } from "react";

/**
 * Hook to capture TradingView chart screenshots and send to AI for analysis.
 */

interface AIAnalysisResult {
  direction: "LONG" | "SHORT" | "HOLD";
  confidence: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number[];
  break_even_trigger: number;
  trailing_stop: {
    enabled: boolean;
    activation_price: number;
    trail_distance: number;
  };
  risk_reward_ratio: number;
  reasoning: string;
  patterns_detected: string[];
}

interface CaptureResult {
  success: boolean;
  imageBase64?: string;
  analysis?: AIAnalysisResult;
  error?: string;
}

export function useChartCapture() {
  const isCapturing = useRef(false);

  const captureElement = useCallback(async (element: HTMLElement): Promise<string | null> => {
    try {
      const html2canvas = (await import("html2canvas")).default;

      const canvas = await html2canvas(element, {
        backgroundColor: "#0f172a",
        scale: 2,
        logging: false,
        useCORS: true,
        allowTaint: true,
      });

      return canvas.toDataURL("image/png").split(",")[1];
    } catch (error) {
      console.error("Failed to capture chart:", error);
      return null;
    }
  }, []);

  const captureChart = useCallback(async (
    chartElement: HTMLElement | null,
    symbol: string,
    timeframes: string[] = ["1H"]
  ): Promise<CaptureResult> => {
    if (!chartElement) {
      return { success: false, error: "No chart element provided" };
    }

    if (isCapturing.current) {
      return { success: false, error: "Capture already in progress" };
    }

    isCapturing.current = true;

    try {
      const imageBase64 = await captureElement(chartElement);

      if (!imageBase64) {
        return { success: false, error: "Failed to capture chart image" };
      }

      const response = await fetch("/api/v1/ai/analyze-chart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          timeframes,
          chart_image: imageBase64,
          request_sl_tp_be_ts: true,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        return { success: false, error: error.detail || "Analysis failed" };
      }

      const analysis = await response.json();

      return { success: true, imageBase64, analysis };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    } finally {
      isCapturing.current = false;
    }
  }, [captureElement]);

  const captureMultipleTimeframes = useCallback(async (
    chartElements: Map<string, HTMLElement>,
    symbol: string
  ): Promise<CaptureResult> => {
    if (chartElements.size === 0) {
      return { success: false, error: "No chart elements provided" };
    }

    if (isCapturing.current) {
      return { success: false, error: "Capture already in progress" };
    }

    isCapturing.current = true;

    try {
      const images: Record<string, string> = {};

      for (const [timeframe, element] of chartElements) {
        const imageBase64 = await captureElement(element);
        if (imageBase64) {
          images[timeframe] = imageBase64;
        }
      }

      if (Object.keys(images).length === 0) {
        return { success: false, error: "Failed to capture any charts" };
      }

      const response = await fetch("/api/v1/ai/analyze-multi-timeframe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          chart_images: images,
          request_sl_tp_be_ts: true,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        return { success: false, error: error.detail || "Analysis failed" };
      }

      const analysis = await response.json();
      return { success: true, analysis };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    } finally {
      isCapturing.current = false;
    }
  }, [captureElement]);

  return {
    captureChart,
    captureMultipleTimeframes,
    isCapturing: isCapturing.current,
  };
}

export type { CaptureResult, AIAnalysisResult };
