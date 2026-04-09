declare module "react-calendar-heatmap" {
  import type { ComponentType } from "react";

  export interface CalendarHeatmapProps {
    startDate: Date | string;
    endDate: Date | string;
    values: { date: string; count: number }[];
    classForValue?: (value: { date: string; count: number } | null) => string;
    tooltipDataAttrs?: (value: { date: string; count: number } | null) => Record<string, string>;
    showWeekdayLabels?: boolean;
    gutterSize?: number;
    horizontal?: boolean;
    showMonthLabels?: boolean;
  }

  const CalendarHeatmap: ComponentType<CalendarHeatmapProps>;
  export default CalendarHeatmap;
}
