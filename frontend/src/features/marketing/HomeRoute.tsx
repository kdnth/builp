import { Center, Loader } from '@mantine/core'
import { useAuthSession } from '../../lib/auth'
import CourseListPage from '../course-catalog/CourseListPage'
import LandingPage from './LandingPage'

export default function HomeRoute() {
  const session = useAuthSession()

  if (session.isPending) {
    return (
      <Center py={80}>
        <Loader />
      </Center>
    )
  }

  return session.data ? <CourseListPage /> : <LandingPage />
}
