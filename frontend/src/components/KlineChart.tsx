import { useEffect, useRef, useCallback, useState } from 'react'
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts'
import type { IChartApi, ISeriesApi, CandlestickData, HistogramData } from 'lightweight-charts'
import type { KlineBar } from '../types/api'

interface Props {
  data: KlineBar[]
  days: number
  onDaysChange: (days: number) => void
}

const DAYS_OPTIONS = [20, 60, 120]

export default function KlineChart({ data, days, onDaysChange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const [error, setError] = useState('')

  const resizeObserver = useRef<ResizeObserver | null>(null)

  const buildChart = useCallback(() => {
    const container = containerRef.current
    if (!container || data.length === 0) return

    // Cleanup old
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
    }

    const { clientWidth: width, clientHeight: height } = container
    if (width < 100) return

    try {
      const chart = createChart(container, {
        width,
        height: Math.max(height, 360),
        layout: {
          background: { type: ColorType.Solid, color: '#ffffff' },
          textColor: '#888',
        },
        grid: {
          vertLines: { color: '#f0f0f0' },
          horzLines: { color: '#f0f0f0' },
        },
        crosshair: {
          mode: 0,
        },
        rightPriceScale: {
          borderColor: '#e0e0e0',
        },
        timeScale: {
          borderColor: '#e0e0e0',
          timeVisible: false,
        },
      })

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#d32f2f',
        downColor: '#2e7d32',
        borderUpColor: '#d32f2f',
        borderDownColor: '#2e7d32',
        wickUpColor: '#d32f2f',
        wickDownColor: '#2e7d32',
      })

      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      })

      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      })

      const candleData: CandlestickData[] = data.map(k => ({
        time: k.tradeDate,
        open: k.open,
        high: k.high,
        low: k.low,
        close: k.close,
      }))
      candleSeries.setData(candleData)

      const volumeData: HistogramData[] = data.map(k => ({
        time: k.tradeDate,
        value: k.volume,
        color: k.close >= k.open ? '#d32f2f40' : '#2e7d3240',
      }))
      volumeSeries.setData(volumeData)

      chart.timeScale().fitContent()

      candleSeriesRef.current = candleSeries
      volumeSeriesRef.current = volumeSeries
      chartRef.current = chart
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'K线图渲染失败')
    }
  }, [data])

  useEffect(() => {
    buildChart()

    const container = containerRef.current
    if (!container) return

    resizeObserver.current = new ResizeObserver(() => {
      const chart = chartRef.current
      if (chart) {
        const w = container.clientWidth
        chart.applyOptions({ width: w })
      }
    })
    resizeObserver.current.observe(container)

    return () => {
      resizeObserver.current?.disconnect()
      chartRef.current?.remove()
    }
  }, [buildChart])

  if (error) {
    return <div className="card"><p className="error">{error}</p></div>
  }

  if (data.length === 0) {
    return (
      <div className="card">
        <h3>K 线图</h3>
        <p className="hint">暂无 K 线数据，请先采集</p>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="kline-header">
        <h3>K 线图</h3>
        <div className="kline-days">
          {DAYS_OPTIONS.map(d => (
            <button
              key={d}
              className={`day-btn ${days === d ? 'active' : ''}`}
              onClick={() => onDaysChange(d)}
            >
              {d}日
            </button>
          ))}
        </div>
      </div>
      <div ref={containerRef} className="kline-container" />
    </div>
  )
}
