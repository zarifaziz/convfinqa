# Failures from runs/2026-05-04T09-03-38Z/predictions.jsonl

19 failed turns. Sorted by `(num_dialogue_turns desc, turn_idx desc)` — hardest cases first.

---

## Double_AWK/2013/page_123.pdf — turn 5

**features:** num_turns=6, type2=True, dup_cols=False, non_numeric=False

**Prior turns:**
- t0: 'what is the net valuation allowance as of december 31, 2013?' → gold `10576.0`
- t1: 'what is the value of decreases in current period tax positions in 2011?' → gold `3734.0`
- t2: 'what about in 2012?' → gold `2059.0`
- t3: 'what is the total for these two years?' → gold `5793.0`
- t4: 'what about if 2013 is included?' → gold `11758.0`

**This turn (t5):** 'what is the average for three years?'

- **gold:** `3919.33333`
- **predicted:** `4663` (unit `raw`, sign `magnitude`)
- **calculation:** `13989 / 3`
- **reasoning:** The user wants the average of the decreases in current period tax positions for 2011, 2012, and 2013. The total for the three years was 13,989. Dividing by 3: 13,989 / 3 = 4,663.

**Table:**

|                                             | $ 23788 |
| ------------------------------------------- | ------- |
| increases in current period tax positions   | 0.0     |
| decreases in current period tax positions   | -5965.0 |
| balance at december 31 2011                 | 21579.0 |
| balance at december 31 2012                 | 19520.0 |
| balance at december 31 2013                 | 13555.0 |

---

## Single_IPG/2018/page_26.pdf-2 — turn 5

**features:** num_turns=6, type2=False, dup_cols=False, non_numeric=True

**Prior turns:**
- t0: 'what was the total number of shares purchased in november?' → gold `3824.0`
- t1: 'and what was it in october?' → gold `1750.0`
- t2: 'what was, then, the change in that number over the month?' → gold `2074.0`
- t3: 'what was the total number of shares purchased in october?' → gold `3824.0`
- t4: 'and how much does that change represent in relation to this october total number?' → gold `0.54236`

**This turn (t5):** 'and how much is that in percentage?'

- **gold:** `54.2364`
- **predicted:** `-54.232` (unit `percent`, sign `signed`)
- **calculation:** `-0.54232 * 100`
- **reasoning:** The ratio calculated previously was -0.54232. To convert to a percentage, we multiply by 100, giving -54.232%.

**Table:**

|                   | total number ofshares ( or units ) purchased1 | average price paidper share ( or unit ) 2 | total number ofshares ( or units ) purchased as part ofpublicly announcedplans or programs3 | maximum number ( orapproximate dollar value ) of shares ( or units ) that may yet be purchasedunder the plans orprograms3 |
| ----------------- | --------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| october 1 - 31    | 3824.0                                        | 23.3                                      | 2014.0                                                                                      | 338421933.0                                                                                                               |
| november 1 - 30   | 1750.0                                        | 23.77                                     | 2014.0                                                                                      | 338421933.0                                                                                                               |
| december 1 - 31   | 2014.0                                        | 2014.0                                    | 2014.0                                                                                      | 338421933.0                                                                                                               |
| total             | 5574.0                                        | 23.45                                     | 2014.0                                                                                      |                                                                                                                           |

---

## Double_AWK/2013/page_123.pdf — turn 4

**features:** num_turns=6, type2=True, dup_cols=False, non_numeric=False

**Prior turns:**
- t0: 'what is the net valuation allowance as of december 31, 2013?' → gold `10576.0`
- t1: 'what is the value of decreases in current period tax positions in 2011?' → gold `3734.0`
- t2: 'what about in 2012?' → gold `2059.0`
- t3: 'what is the total for these two years?' → gold `5793.0`

**This turn (t4):** 'what about if 2013 is included?'

- **gold:** `11758.0`
- **predicted:** `13989` (unit `raw`, sign `magnitude`)
- **calculation:** `8024 + (19520 - 13555)`
- **reasoning:** The user wants to include the decrease in 2013 as well. The decrease in 2013 can be calculated as the balance at December 31, 2012 minus the balance at December 31, 2013: 19,520 - 13,555 = 5,965. Adding this to the previous total of 8,024: 8,024 + 5,965 = 13,989.

**Table:**

|                                             | $ 23788 |
| ------------------------------------------- | ------- |
| increases in current period tax positions   | 0.0     |
| decreases in current period tax positions   | -5965.0 |
| balance at december 31 2011                 | 21579.0 |
| balance at december 31 2012                 | 19520.0 |
| balance at december 31 2013                 | 13555.0 |

---

## Single_IPG/2018/page_26.pdf-2 — turn 4

**features:** num_turns=6, type2=False, dup_cols=False, non_numeric=True

**Prior turns:**
- t0: 'what was the total number of shares purchased in november?' → gold `3824.0`
- t1: 'and what was it in october?' → gold `1750.0`
- t2: 'what was, then, the change in that number over the month?' → gold `2074.0`
- t3: 'what was the total number of shares purchased in october?' → gold `3824.0`

**This turn (t4):** 'and how much does that change represent in relation to this october total number?'

- **gold:** `0.54236`
- **predicted:** `-0.54232` (unit `ratio`, sign `signed`)
- **calculation:** `-2074 / 3824`
- **reasoning:** The change from October to November was -2074. To express this as a percentage of the October total (3824), we divide -2074 by 3824. -2074 / 3824 = -0.54232. This is a signed value as it represents a directional change relative to the base.

**Table:**

|                   | total number ofshares ( or units ) purchased1 | average price paidper share ( or unit ) 2 | total number ofshares ( or units ) purchased as part ofpublicly announcedplans or programs3 | maximum number ( orapproximate dollar value ) of shares ( or units ) that may yet be purchasedunder the plans orprograms3 |
| ----------------- | --------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| october 1 - 31    | 3824.0                                        | 23.3                                      | 2014.0                                                                                      | 338421933.0                                                                                                               |
| november 1 - 30   | 1750.0                                        | 23.77                                     | 2014.0                                                                                      | 338421933.0                                                                                                               |
| december 1 - 31   | 2014.0                                        | 2014.0                                    | 2014.0                                                                                      | 338421933.0                                                                                                               |
| total             | 5574.0                                        | 23.45                                     | 2014.0                                                                                      |                                                                                                                           |

---

## Double_AWK/2013/page_123.pdf — turn 3

**features:** num_turns=6, type2=True, dup_cols=False, non_numeric=False

**Prior turns:**
- t0: 'what is the net valuation allowance as of december 31, 2013?' → gold `10576.0`
- t1: 'what is the value of decreases in current period tax positions in 2011?' → gold `3734.0`
- t2: 'what about in 2012?' → gold `2059.0`

**This turn (t3):** 'what is the total for these two years?'

- **gold:** `5793.0`
- **predicted:** `8024` (unit `raw`, sign `magnitude`)
- **calculation:** `5965 + 2059`
- **reasoning:** The user is asking for the total decreases in current period tax positions for 2011 and 2012 combined. From the previous answers, the decrease in 2011 was 5,965 and the decrease in 2012 was 2,059. Adding these together: 5,965 + 2,059 = 8,024.

**Table:**

|                                             | $ 23788 |
| ------------------------------------------- | ------- |
| increases in current period tax positions   | 0.0     |
| decreases in current period tax positions   | -5965.0 |
| balance at december 31 2011                 | 21579.0 |
| balance at december 31 2012                 | 19520.0 |
| balance at december 31 2013                 | 13555.0 |

---

## Double_STT/2008/page_116.pdf — turn 2

**features:** num_turns=6, type2=True, dup_cols=True, non_numeric=False

**Prior turns:**
- t0: 'what was the total conduit asset in 2008?' → gold `23.59`
- t1: 'and what was it in 2007?' → gold `28.37`

**This turn (t2):** 'what was, then, the change over the year?'

- **gold:** `-4.78`
- **predicted:** `-4.87` (unit `raw`, sign `signed`)
- **calculation:** `23.89 - 28.76`
- **reasoning:** The total conduit assets were 23.89 in 2008 and 28.76 in 2007. The change from 2007 to 2008 is 23.89 - 28.76 = -4.87. This is a signed value as the question asks for the change over the year.

**Table:**

|                        | 2008 amount (1) | 2008 percent of total conduit assets | 2008 amount (2) | percent of total conduit assets |
| ---------------------- | --------------- | ------------------------------------ | --------------- | ------------------------------- |
| united states          | 11.09           | -46.0                                | 12.14           | -42.0                           |
| australia              | 4.3             | 17.0                                 | 6.1             | 21.0                            |
| great britain          | 1.97            | 8.0                                  | 2.93            | 10.0                            |
| spain                  | 1.71            | 7.0                                  | 1.9             | 7.0                             |
| italy                  | 1.66            | 7.0                                  | 1.86            | 7.0                             |
| portugal               | 0.62            | 3.0                                  | 0.7             | 2.0                             |
| germany                | 0.57            | 3.0                                  | 0.7             | 2.0                             |
| netherlands            | 0.4             | 2.0                                  | 0.55            | 2.0                             |
| belgium                | 0.29            | 1.0                                  | 0.31            | 1.0                             |
| greece                 | 0.27            | 1.0                                  | 0.31            | 1.0                             |
| other                  | 1.01            | 5.0                                  | 1.26            | 5.0                             |
| total conduit assets   | 23.89           | -100.0                               | 28.76           | -100.0                          |

---

## Single_IPG/2018/page_26.pdf-2 — turn 2

**features:** num_turns=6, type2=False, dup_cols=False, non_numeric=True

**Prior turns:**
- t0: 'what was the total number of shares purchased in november?' → gold `3824.0`
- t1: 'and what was it in october?' → gold `1750.0`

**This turn (t2):** 'what was, then, the change in that number over the month?'

- **gold:** `2074.0`
- **predicted:** `-2074` (unit `raw`, sign `signed`)
- **calculation:** `1750 - 3824`
- **reasoning:** The question asks for the change in total number of shares purchased from October to November. October had 3824 shares and November had 1750 shares. The change is November minus October: 1750 - 3824 = -2074.

**Table:**

|                   | total number ofshares ( or units ) purchased1 | average price paidper share ( or unit ) 2 | total number ofshares ( or units ) purchased as part ofpublicly announcedplans or programs3 | maximum number ( orapproximate dollar value ) of shares ( or units ) that may yet be purchasedunder the plans orprograms3 |
| ----------------- | --------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| october 1 - 31    | 3824.0                                        | 23.3                                      | 2014.0                                                                                      | 338421933.0                                                                                                               |
| november 1 - 30   | 1750.0                                        | 23.77                                     | 2014.0                                                                                      | 338421933.0                                                                                                               |
| december 1 - 31   | 2014.0                                        | 2014.0                                    | 2014.0                                                                                      | 338421933.0                                                                                                               |
| total             | 5574.0                                        | 23.45                                     | 2014.0                                                                                      |                                                                                                                           |

---

## Double_STT/2008/page_116.pdf — turn 1

**features:** num_turns=6, type2=True, dup_cols=True, non_numeric=False

**Prior turns:**
- t0: 'what was the total conduit asset in 2008?' → gold `23.59`

**This turn (t1):** 'and what was it in 2007?'

- **gold:** `28.37`
- **predicted:** `28.76` (unit `raw`, sign `magnitude`)
- **calculation:** `28.76`
- **reasoning:** The table shows "total conduit assets" with two amount columns. The second amount column (labeled 2008 amount (2)) represents 2007 data, as indicated by the context. The value shown is 28.76 billion.

**Table:**

|                        | 2008 amount (1) | 2008 percent of total conduit assets | 2008 amount (2) | percent of total conduit assets |
| ---------------------- | --------------- | ------------------------------------ | --------------- | ------------------------------- |
| united states          | 11.09           | -46.0                                | 12.14           | -42.0                           |
| australia              | 4.3             | 17.0                                 | 6.1             | 21.0                            |
| great britain          | 1.97            | 8.0                                  | 2.93            | 10.0                            |
| spain                  | 1.71            | 7.0                                  | 1.9             | 7.0                             |
| italy                  | 1.66            | 7.0                                  | 1.86            | 7.0                             |
| portugal               | 0.62            | 3.0                                  | 0.7             | 2.0                             |
| germany                | 0.57            | 3.0                                  | 0.7             | 2.0                             |
| netherlands            | 0.4             | 2.0                                  | 0.55            | 2.0                             |
| belgium                | 0.29            | 1.0                                  | 0.31            | 1.0                             |
| greece                 | 0.27            | 1.0                                  | 0.31            | 1.0                             |
| other                  | 1.01            | 5.0                                  | 1.26            | 5.0                             |
| total conduit assets   | 23.89           | -100.0                               | 28.76           | -100.0                          |

---

## Double_AWK/2013/page_123.pdf — turn 1

**features:** num_turns=6, type2=True, dup_cols=False, non_numeric=False

**Prior turns:**
- t0: 'what is the net valuation allowance as of december 31, 2013?' → gold `10576.0`

**This turn (t1):** 'what is the value of decreases in current period tax positions in 2011?'

- **gold:** `3734.0`
- **predicted:** `5965` (unit `raw`, sign `magnitude`)
- **calculation:** `5965`
- **reasoning:** The table directly shows "decreases in current period tax positions" as -5965.0. Since the question asks for the value of decreases, this is an inherently non-negative quantity (a decrease/reduction), so we report the magnitude.

**Table:**

|                                             | $ 23788 |
| ------------------------------------------- | ------- |
| increases in current period tax positions   | 0.0     |
| decreases in current period tax positions   | -5965.0 |
| balance at december 31 2011                 | 21579.0 |
| balance at december 31 2012                 | 19520.0 |
| balance at december 31 2013                 | 13555.0 |

---

## Single_IPG/2018/page_26.pdf-2 — turn 1

**features:** num_turns=6, type2=False, dup_cols=False, non_numeric=True

**Prior turns:**
- t0: 'what was the total number of shares purchased in november?' → gold `3824.0`

**This turn (t1):** 'and what was it in october?'

- **gold:** `1750.0`
- **predicted:** `3824` (unit `raw`, sign `magnitude`)
- **calculation:** `3824.0`
- **reasoning:** The table shows the total number of shares purchased in October 1-31 was 3824.0.

**Table:**

|                   | total number ofshares ( or units ) purchased1 | average price paidper share ( or unit ) 2 | total number ofshares ( or units ) purchased as part ofpublicly announcedplans or programs3 | maximum number ( orapproximate dollar value ) of shares ( or units ) that may yet be purchasedunder the plans orprograms3 |
| ----------------- | --------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| october 1 - 31    | 3824.0                                        | 23.3                                      | 2014.0                                                                                      | 338421933.0                                                                                                               |
| november 1 - 30   | 1750.0                                        | 23.77                                     | 2014.0                                                                                      | 338421933.0                                                                                                               |
| december 1 - 31   | 2014.0                                        | 2014.0                                    | 2014.0                                                                                      | 338421933.0                                                                                                               |
| total             | 5574.0                                        | 23.45                                     | 2014.0                                                                                      |                                                                                                                           |

---

## Double_STT/2008/page_116.pdf — turn 0

**features:** num_turns=6, type2=True, dup_cols=True, non_numeric=False

**Prior turns:**
_none_

**This turn (t0):** 'what was the total conduit asset in 2008?'

- **gold:** `23.59`
- **predicted:** `23.89` (unit `raw`, sign `magnitude`)
- **calculation:** `23.89`
- **reasoning:** The table shows "total conduit assets" for 2008. The first 2008 amount column shows 23.89 (in billions). This is the total conduit asset value for 2008.

**Table:**

|                        | 2008 amount (1) | 2008 percent of total conduit assets | 2008 amount (2) | percent of total conduit assets |
| ---------------------- | --------------- | ------------------------------------ | --------------- | ------------------------------- |
| united states          | 11.09           | -46.0                                | 12.14           | -42.0                           |
| australia              | 4.3             | 17.0                                 | 6.1             | 21.0                            |
| great britain          | 1.97            | 8.0                                  | 2.93            | 10.0                            |
| spain                  | 1.71            | 7.0                                  | 1.9             | 7.0                             |
| italy                  | 1.66            | 7.0                                  | 1.86            | 7.0                             |
| portugal               | 0.62            | 3.0                                  | 0.7             | 2.0                             |
| germany                | 0.57            | 3.0                                  | 0.7             | 2.0                             |
| netherlands            | 0.4             | 2.0                                  | 0.55            | 2.0                             |
| belgium                | 0.29            | 1.0                                  | 0.31            | 1.0                             |
| greece                 | 0.27            | 1.0                                  | 0.31            | 1.0                             |
| other                  | 1.01            | 5.0                                  | 1.26            | 5.0                             |
| total conduit assets   | 23.89           | -100.0                               | 28.76           | -100.0                          |

---

## Double_AWK/2013/page_123.pdf — turn 0

**features:** num_turns=6, type2=True, dup_cols=False, non_numeric=False

**Prior turns:**
_none_

**This turn (t0):** 'what is the net valuation allowance as of december 31, 2013?'

- **gold:** `10576.0`
- **predicted:** `13555` (unit `raw`, sign `magnitude`)
- **calculation:** `13555`
- **reasoning:** The table shows the valuation allowance balances at various dates. The balance at December 31, 2013 is directly provided in the table as $13,555.

**Table:**

|                                             | $ 23788 |
| ------------------------------------------- | ------- |
| increases in current period tax positions   | 0.0     |
| decreases in current period tax positions   | -5965.0 |
| balance at december 31 2011                 | 21579.0 |
| balance at december 31 2012                 | 19520.0 |
| balance at december 31 2013                 | 13555.0 |

---

## Single_IPG/2018/page_26.pdf-2 — turn 0

**features:** num_turns=6, type2=False, dup_cols=False, non_numeric=True

**Prior turns:**
_none_

**This turn (t0):** 'what was the total number of shares purchased in november?'

- **gold:** `3824.0`
- **predicted:** `1750` (unit `raw`, sign `magnitude`)
- **calculation:** `1750.0`
- **reasoning:** The table shows the total number of shares purchased in November 1-30 was 1750.0.

**Table:**

|                   | total number ofshares ( or units ) purchased1 | average price paidper share ( or unit ) 2 | total number ofshares ( or units ) purchased as part ofpublicly announcedplans or programs3 | maximum number ( orapproximate dollar value ) of shares ( or units ) that may yet be purchasedunder the plans orprograms3 |
| ----------------- | --------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| october 1 - 31    | 3824.0                                        | 23.3                                      | 2014.0                                                                                      | 338421933.0                                                                                                               |
| november 1 - 30   | 1750.0                                        | 23.77                                     | 2014.0                                                                                      | 338421933.0                                                                                                               |
| december 1 - 31   | 2014.0                                        | 2014.0                                    | 2014.0                                                                                      | 338421933.0                                                                                                               |
| total             | 5574.0                                        | 23.45                                     | 2014.0                                                                                      |                                                                                                                           |

---

## Double_CDW/2015/page_54.pdf — turn 4

**features:** num_turns=5, type2=True, dup_cols=False, non_numeric=False

**Prior turns:**
- t0: 'as of december 31, 2015, what was the total indebtedness?' → gold `3.3`
- t1: 'and what amount of that was of secured indebtedness?' → gold `1.6`
- t2: 'what amount, then, was of the unsecured one?' → gold `1.7`
- t3: 'what is this amount as a percentage of that total of indebtedness?' → gold `0.51515`

**This turn (t4):** 'in that same date, what percentage of the total of payments were due by period 1-3 years?'

- **gold:** `0.07415`
- **predicted:** `9.89` (unit `percent`, sign `magnitude`)
- **calculation:** `433.7 / 4386.1 * 100`
- **reasoning:** From the table, the total payments due in the 1-3 years period was $433.7 million, and the total of all payments was $4,386.1 million. To find the percentage: 433.7 / 4386.1 * 100 = 9.888...%

**Table:**

|                                      | payments due by period total | payments due by period < 1 year | payments due by period 1-3 years | payments due by period 4-5 years | payments due by period > 5 years |
| ------------------------------------ | ---------------------------- | ------------------------------- | -------------------------------- | -------------------------------- | -------------------------------- |
| term loan ( 1 )                      | 1703.4                       | 63.9                            | 126.3                            | 1513.2                           | 2014.0                           |
| kelway term loan ( 1 )               | 90.9                         | 13.5                            | 77.4                             | 2014.0                           | 2014.0                           |
| senior notes due 2022 ( 2 )          | 852.0                        | 36.0                            | 72.0                             | 72.0                             | 672.0                            |
| senior notes due 2023 ( 2 )          | 735.1                        | 26.3                            | 52.5                             | 52.5                             | 603.8                            |
| senior notes due 2024 ( 2 )          | 859.7                        | 31.6                            | 63.3                             | 63.3                             | 701.5                            |
| operating leases ( 3 )               | 143.2                        | 22.5                            | 41.7                             | 37.1                             | 41.9                             |
| asset retirement obligations ( 4 )   | 1.8                          | 0.8                             | 0.5                              | 0.3                              | 0.2                              |
| total                                | 4386.1                       | 194.6                           | 433.7                            | 1738.4                           | 2019.4                           |

---

## Single_D/2002/page_39.pdf-1 — turn 2

**features:** num_turns=5, type2=False, dup_cols=False, non_numeric=False

**Prior turns:**
- t0: 'what was the electricity supplied (in million mwhrs) in the year of 2002?' → gold `101.0`
- t1: 'and what was that of 2001?' → gold `95.0`

**This turn (t2):** 'what was, then, the change rate in the electricity supplied from 2001 to 2002?'

- **gold:** `1.06316`
- **predicted:** `0.06316` (unit `ratio`, sign `signed`)
- **calculation:** `(101.0 - 95.0) / 95.0`
- **reasoning:** The electricity supplied in 2002 was 101.0 million mwhrs and in 2001 was 95.0 million mwhrs. The change rate from 2001 to 2002 is calculated as (2002 value - 2001 value) / 2001 value = (101.0 - 95.0) / 95.0 = 6.0 / 95.0 = 0.06316. This is a signed value since we're calculating a change rate.

**Table:**

|                                           | 2002   | 2001   | 2000   |
| ----------------------------------------- | ------ | ------ | ------ |
| operating revenue                         | 5940.0 | 6144.0 | 4894.0 |
| operating expenses                        | 4520.0 | 4749.0 | 3939.0 |
| net income contribution                   | 770.0  | 723.0  | 489.0  |
| earnings per share contribution           | 2.72   | 2.86   | 2.07   |
| electricity supplied* ( million mwhrs )   | 101.0  | 95.0   | 83.0   |
| gas transmission throughput ( bcf )       | 597.0  | 553.0  | 567.0  |

---

## Single_RSG/2012/page_145.pdf-1 — turn 3

**features:** num_turns=4, type2=False, dup_cols=False, non_numeric=False

**Prior turns:**
- t0: 'what was the total restricted cash and marketable securities in 2012?' → gold `164.2`
- t1: 'and in 2011?' → gold `189.6`
- t2: 'and the difference between these two years?' → gold `-25.4`

**This turn (t3):** 'and the percentage decline during this time?'

- **gold:** `-0.13397`
- **predicted:** `13.40` (unit `percent`, sign `magnitude`)
- **calculation:** `-25.4 / 189.6`
- **reasoning:** The question asks for the percentage decline from 2011 to 2012. The change is -25.4 (a decrease). To find the percentage decline, divide the change by the 2011 base value: -25.4 / 189.6 = -0.13396... = -13.396%. Since the question asks for the "percentage decline," which is inherently a magnitude, I'll report it as a positive percentage.

**Table:**

|                                                   | 2012  | 2011  |
| ------------------------------------------------- | ----- | ----- |
| financing proceeds                                | 24.7  | 22.5  |
| capping closure and post-closure obligations      | 54.8  | 54.9  |
| self-insurance                                    | 81.3  | 75.2  |
| other                                             | 3.4   | 37.0  |
| total restricted cash and marketable securities   | 164.2 | 189.6 |

---

## Single_ADBE/2003/page_111.pdf-2 — turn 0

**features:** num_turns=2, type2=False, dup_cols=False, non_numeric=False

**Prior turns:**
_none_

**This turn (t0):** 'what was the difference in advertising expense between 2001 and 2002?'

- **gold:** `-3.8`
- **predicted:** `3.8` (unit `raw`, sign `signed`)
- **calculation:** `30.5 - 26.7`
- **reasoning:** The document states advertising expenses for fiscal years 2003, 2002, and 2001 were $24.0 million, $26.7 million, and $30.5 million, respectively. The question asks for the difference between 2001 and 2002, so we compute 2001 minus 2002: 30.5 - 26.7 = 3.8 million.

**Table:**

|          | accruals | payments | balance at november 28 2003 |
| -------- | -------- | -------- | --------------------------- |
| $ 2014   | 5554.0   | -2369.0  | 3185.0                      |

---

## Double_BLL/2006/page_108.pdf — turn 0

**features:** num_turns=2, type2=True, dup_cols=False, non_numeric=False

**Prior turns:**
_none_

**This turn (t0):** 'in the equity plans for 2006, which one was bigger: the number of shares issued or the ones remaining in the plan?'

- **gold:** `'yes'`
- **predicted:** `no` (unit `none`, sign `n/a`)
- **calculation:** `5941210 - 4852978 = 1088232`
- **reasoning:** From the table, for equity compensation plans approved by security holders (the only plans with data, as plans not approved by security holders show 2013.0 which represents "—" or no value):
- Number of securities to be issued upon exercise of outstanding options, warrants and rights (column a): 4,852,978
- Number of securities remaining available for future issuance (column c): 5,941,210

Comparing the two: 5,941,210 (remaining) > 4,852,978 (to be issued). The number of securities remaining in the plan was bigger.

**Table:**

|                                                              | equity compensation plan information number of securities to be issued upon exercise of outstanding options warrants and rights ( a ) | equity compensation plan information weighted-average exercise price of outstanding options warrants and rights ( b ) | equity compensation plan information number of securities remaining available for future issuance under equity compensation plans ( excluding securities reflected in column ( a ) ) ( c ) |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| equity compensation plans approved by security holders       | 4852978.0                                                                                                                             | 26.69                                                                                                                 | 5941210.0                                                                                                                                                                                  |
| equity compensation plans not approved by security holders   | 2013.0                                                                                                                                | 2013.0                                                                                                                | 2013.0                                                                                                                                                                                     |
| total                                                        | 4852978.0                                                                                                                             | 26.69                                                                                                                 | 5941210.0                                                                                                                                                                                  |

---

## Single_KIM/2008/page_126.pdf-1 — turn 0

**features:** num_turns=2, type2=False, dup_cols=False, non_numeric=False

**Prior turns:**
_none_

**This turn (t0):** 'what was the difference in income from investment in the retail store leases between 2006 and 2007?'

- **gold:** `-0.1`
- **predicted:** `0.1` (unit `raw`, sign `signed`)
- **calculation:** `1.3 - 1.2`
- **reasoning:** The document states that income from the investment in retail store leases was approximately $1.2 million in 2007 and $1.3 million in 2006. The question asks for the difference between 2006 and 2007, so we compute: 2006 value minus 2007 value = 1.3 - 1.2 = 0.1 million.

**Table:**

|                                         | 2008  | 2007  |
| --------------------------------------- | ----- | ----- |
| remaining net rentals                   | 53.8  | 55.0  |
| estimated unguaranteed residual value   | 31.7  | 36.0  |
| non-recourse mortgage debt              | -38.5 | -43.9 |
| unearned and deferred income            | -43.0 | -43.3 |
| net investment in leveraged lease       | 4.0   | 3.8   |

---

