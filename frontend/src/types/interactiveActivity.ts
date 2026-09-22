import type { Categorize } from './categorize'
import type { FillBlank } from './fillBlank'
import type { Matching } from './matching'
import type { MultipleChoice } from './multipleChoice'
import type { Numeric } from './numeric'
import type { Ordering } from './ordering'

export type InteractiveActivity =
  Matching | FillBlank | MultipleChoice | Ordering | Categorize | Numeric
