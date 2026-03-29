import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  KPIEntry,
  Task,
  AutomationItem,
  ServicePlan,
  ActionLog,
  AppSettings,
  WeeklyReport,
} from '../types'

interface StoreState {
  // State
  kpis: KPIEntry[]
  tasks: Task[]
  automations: AutomationItem[]
  servicePlans: ServicePlan[]
  logs: ActionLog[]
  settings: AppSettings
  weeklyReports: WeeklyReport[]

  // KPI actions
  addKPI: (entry: KPIEntry) => void
  updateKPI: (id: string, entry: Partial<KPIEntry>) => void
  removeKPI: (id: string) => void

  // Task actions
  addTask: (task: Task) => void
  updateTask: (id: string, task: Partial<Task>) => void
  removeTask: (id: string) => void
  setTasks: (tasks: Task[]) => void

  // Automation actions
  addAutomation: (item: AutomationItem) => void
  updateAutomation: (id: string, item: Partial<AutomationItem>) => void

  // Service plan actions
  setServicePlans: (plans: ServicePlan[]) => void

  // Log actions
  addLog: (log: ActionLog) => void

  // Settings actions
  updateSettings: (settings: Partial<AppSettings>) => void

  // Weekly report actions
  addWeeklyReport: (report: WeeklyReport) => void
}

const defaultSettings: AppSettings = {
  anthropicApiKey: '',
  geminiApiKey: '',
  googleClientId: '',
  googleApiKey: '',
  driveRootFolderId: '',
  kpiSheetId: '',
  progressSheetId: '',
}

export const useStore = create<StoreState>()(
  persist(
    (set) => ({
      // Initial state
      kpis: [],
      tasks: [],
      automations: [],
      servicePlans: [],
      logs: [],
      settings: defaultSettings,
      weeklyReports: [],

      // KPI actions
      addKPI: (entry) =>
        set((state) => ({ kpis: [...state.kpis, entry] })),
      updateKPI: (id, entry) =>
        set((state) => ({
          kpis: state.kpis.map((k) => (k.id === id ? { ...k, ...entry } : k)),
        })),
      removeKPI: (id) =>
        set((state) => ({ kpis: state.kpis.filter((k) => k.id !== id) })),

      // Task actions
      addTask: (task) =>
        set((state) => ({ tasks: [...state.tasks, task] })),
      updateTask: (id, task) =>
        set((state) => ({
          tasks: state.tasks.map((t) => (t.id === id ? { ...t, ...task } : t)),
        })),
      removeTask: (id) =>
        set((state) => ({ tasks: state.tasks.filter((t) => t.id !== id) })),
      setTasks: (tasks) => set({ tasks }),

      // Automation actions
      addAutomation: (item) =>
        set((state) => ({ automations: [...state.automations, item] })),
      updateAutomation: (id, item) =>
        set((state) => ({
          automations: state.automations.map((a) =>
            a.id === id ? { ...a, ...item } : a
          ),
        })),

      // Service plan actions
      setServicePlans: (plans) => set({ servicePlans: plans }),

      // Log actions
      addLog: (log) =>
        set((state) => ({ logs: [...state.logs, log] })),

      // Settings actions
      updateSettings: (settings) =>
        set((state) => ({
          settings: { ...state.settings, ...settings },
        })),

      // Weekly report actions
      addWeeklyReport: (report) =>
        set((state) => ({ weeklyReports: [...state.weeklyReports, report] })),
    }),
    {
      name: 'sns-ai-tool-store',
    }
  )
)
