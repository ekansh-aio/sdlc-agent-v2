from common.db.postgres_client import PostgresClient

class PromptManager:
    def __init__(self):
        self.db = PostgresClient()

    def get_prompt(self, ai_helper_name: str, agent_name: str):
        query = """
        SELECT prompt_content FROM agent_prompts
        WHERE ai_helper_name = %s AND agent_name = %s
        ORDER BY version DESC LIMIT 1
        """
        try:
            result = self.db.fetch_one(query, (ai_helper_name, agent_name))
            if result is None:
                raise ValueError(f"No content found for {ai_helper_name} and {agent_name} ")
            return result["prompt_content"]
        except Exception as e:
            raise RuntimeError(f"Error fetching value for name {ai_helper_name} and {agent_name}")

        
    
    def get_prompt_parameter(self, ai_helper_name: str, agent_name: str):
        query = """
        SELECT prompt_parameter FROM agent_prompts
        WHERE ai_helper_name = %s AND agent_name = %s
        ORDER BY version DESC LIMIT 1
        """
        result = self.db.fetch_one(query, (ai_helper_name, agent_name))
        return result["prompt_parameter"]
    
    def insert_promt(self, ai_helper_name: str, agent_name: str, prompt_content: str, prompt_parameter: list[str] = "") -> int:
        max_version_query = """
        SELECT COALESCE(MAX(version), 0) + 1 AS next_version
        FROM agent_prompts
        WHERE ai_helper_name = %s AND agent_name = %s
        """
        next_version = self.db.fetch_one(max_version_query,(ai_helper_name, agent_name))["next_version"]
        
        insert_query = """
        INSERT INTO agent_prompts (ai_helper_name, agent_name, prompt_content, prompt_parameter, version)
        VALUES(%s, %s, %s, %s, %s)
        RETURNING id
        """
        self.db.execute_query(insert_query, (ai_helper_name, agent_name, prompt_content, next_version))
        return self.cursor.fetchone()["id"]
    
    def delete_prompt(self, prompt_id: int):
        query = """
        DELETE FROM agent_prompts WHERE id = %s
        """
        self.db.execute_query(query, (prompt_id))

    def create_table(self, create_table_sql: str):
        self.db.execute_query(create_table_sql)