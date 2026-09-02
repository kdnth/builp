import '@mantine/core/styles.css'
import { createTheme, MantineProvider } from '@mantine/core'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import CourseListPage from './features/course-catalog/CourseListPage'
import CourseTreePage from './features/course-catalog/CourseTreePage'
import UnitPage from './features/lesson-viewer/UnitPage'

const theme = createTheme({
  primaryColor: 'indigo',
  defaultRadius: 'md',
})

function App() {
  return (
    <MantineProvider theme={theme}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<CourseListPage />} />
          <Route path="/courses/:courseId" element={<CourseTreePage />} />
          <Route
            path="/courses/:courseId/units/:unitId"
            element={<UnitPage />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </MantineProvider>
  )
}

export default App
