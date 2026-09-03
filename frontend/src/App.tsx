import '@mantine/core/styles.css'
import { createTheme, MantineProvider } from '@mantine/core'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './features/layout/AppLayout'
import HomeRoute from './features/marketing/HomeRoute'
import SignInPage from './features/auth/SignInPage'
import SignUpPage from './features/auth/SignUpPage'
import CourseTreePage from './features/course-catalog/CourseTreePage'
import UploadCoursePage from './features/course-catalog/UploadCoursePage'
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
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomeRoute />} />
            <Route path="/sign-in" element={<SignInPage />} />
            <Route path="/sign-up" element={<SignUpPage />} />
            <Route path="/courses/new" element={<UploadCoursePage />} />
            <Route path="/courses/:courseId" element={<CourseTreePage />} />
            <Route
              path="/courses/:courseId/units/:unitId"
              element={<UnitPage />}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </MantineProvider>
  )
}

export default App
