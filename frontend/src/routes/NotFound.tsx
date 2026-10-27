import { Link as RouterLink } from "react-router-dom";
import StatusMessagePanel from "../components/StatusMessagePanel";
import { Button } from "../components/ui/button";

export default function NotFound() {
  return (
    <StatusMessagePanel
      page
      title="페이지를 찾을 수 없습니다."
      description="요청한 주소가 없거나 이동되었을 수 있습니다."
    >
      <RouterLink to="/">
        <Button variant="outline">홈으로</Button>
      </RouterLink>
    </StatusMessagePanel>
  );
}
