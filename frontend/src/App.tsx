import '@mantine/core/styles.css'
import { createTheme, MantineProvider, virtualColor } from '@mantine/core'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './features/layout/AppLayout'
import HomeRoute from './features/marketing/HomeRoute'
import SignInPage from './features/auth/SignInPage'
import SignUpPage from './features/auth/SignUpPage'
import CourseTreePage from './features/course-catalog/CourseTreePage'
import UploadCoursePage from './features/course-catalog/UploadCoursePage'
import UnitPage from './features/lesson-viewer/UnitPage'

const theme = createTheme({
  fontFamily: 'Jost, sans-serif',
  headings: { fontFamily: 'Jost, sans-serif' },
  primaryColor: 'primary',
  primaryShade: { light: 9, dark: 7 },
  defaultRadius: 'md',
  colors: {
    // Primary color, light mode: #7B00B9
    brandLight: [
      '#f8ebff',
      '#edd1fb',
      '#db9ef9',
      '#c968f9',
      '#b93df8',
      '#af25f8',
      '#ab1bf9',
      '#9611de',
      '#850bc6',
      '#7b00b9',
    ],
    // Primary color, dark mode: #B529B5
    brandDark: [
      '#ffecff',
      '#f8d8f8',
      '#edaeed',
      '#e282e2',
      '#d95cd8',
      '#d345d3',
      '#d138d1',
      '#b529b5',
      '#a522a6',
      '#911791',
    ],
    primary: virtualColor({
      name: 'primary',
      light: 'brandLight',
      dark: 'brandDark',
    }),
  },
})

function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="auto">
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
