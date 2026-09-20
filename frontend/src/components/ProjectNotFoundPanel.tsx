import { Link as RouterLink } from "react-router-dom";
import { Button } from "./ui/button";
import StatusMessagePanel from "./StatusMessagePanel";

export default function ProjectNotFoundPanel() {
  return (
    <StatusMessagePanel
      page
      title="프로젝트를 찾을 수 없습니다."
      description="요청한 프로젝트가 없거나 삭제되었을 수 있습니다."
    >
      <RouterLink to="/projects">
        <Button variant="outline">목록으로</Button>
      </RouterLink>
    </StatusMessagePanel>
  );
}
