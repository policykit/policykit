from django.core.management import utils


def get_env_file(filename: str) -> list:
    with open(filename) as f:
        return [line for line in f.readlines()]


def set_env_file(filename: str, file_content: list) -> None:
    with open(filename, "w+") as f:
        f.writelines(line for line in file_content)


def update_env_file(file_content: list, **kwargs: dict):
    def uncomment_all_lines():
        for index, ele in enumerate(file_content):
            if ele.startswith("#"):
                ele = ele[1:]
                ele = ele.strip()
                file_content[index] = ele
    uncomment_all_lines()

    for k, v in kwargs.items():
        for index, ele in enumerate(file_content):
            if ele.startswith(k):
                file_content[index] = f"{k}={v}\n"
            elif not ele.endswith("\n"):
                file_content[index] = f"{ele}\n"
    return file_content


if __name__ == '__main__':
    set_filename = "metagov/policykit/.env"
    get_filename = "metagov/policykit/.env.example"
    env_file = get_env_file(get_filename)
    secret_key = utils.get_random_secret_key()
    kwargs = {
        "DEBUG": "true",
        "DJANGO_SECRET_KEY": secret_key,
        "SERVER_URL": "http://127.0.0.1:8000"
    }
    file_content = update_env_file(env_file, **kwargs)
    set_env_file(set_filename, file_content)
