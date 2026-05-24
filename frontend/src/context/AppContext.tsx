import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { api, type StatusResponse } from '../lib/api'

interface AppContextType {
  status: StatusResponse | null
  loading: boolean
  refresh: () => Promise<void>
  genres: string[]
}

const AppContext = createContext<AppContextType>({
  status: null,
  loading: true,
  refresh: async () => {},
  genres: [],
})

export function AppProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [genres, setGenres] = useState<string[]>([])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [s, g] = await Promise.all([api.getStatus(), api.getGenres()])
      setStatus(s)
      setGenres(g.genres)
    } catch {
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return (
    <AppContext.Provider value={{ status, loading, refresh, genres }}>
      {children}
    </AppContext.Provider>
  )
}

export const useApp = () => useContext(AppContext)
