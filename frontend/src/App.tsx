import '@mantine/core/styles.css'
import sampleCourseData from './data/courses/course-01.json'
import type { Course } from './types/course'
import type { Unit } from './types/unit'
import { createTheme, MantineProvider } from '@mantine/core'
import UnitComponent from './features/lesson-viewer/UnitComponent'

const courseData = sampleCourseData as Course

const theme = createTheme({
  primaryColor: 'indigo',
  defaultRadius: 'md',
})

function App() {
  const unitOne: Unit = courseData.units[0]

  return (
    <MantineProvider theme={theme}>
      <UnitComponent unit={unitOne} />
    </MantineProvider>
  )
}

export default App
