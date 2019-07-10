from locust import HttpLocust, TaskSet, task


class UserBehavior(TaskSet):
    @task(15)
    def health(self):
        self.client.get("/health/")


class User(HttpLocust):
    task_set = UserBehavior
    min_wait = 100
    max_wait = 1000
