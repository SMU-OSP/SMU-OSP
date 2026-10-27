import js from "@eslint/js";
import globals from "globals";
import jsdoc from "eslint-plugin-jsdoc";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier";

/**
 * 이름 규칙 (Microsoft TypeScript 스타일 가이드).
 *
 * https://github.com/microsoft/TypeScript/wiki/Coding-guidelines
 */
const namingSelectors = [
    // 기본값은 camelCase. 밑줄 접두사는 쓰지 않는다.
    {
        selector: "default",
        format: ["camelCase"],
        leadingUnderscore: "forbid",
        trailingUnderscore: "forbid",
    },
    // 모듈 상수는 UPPER_CASE, React 컴포넌트는 PascalCase를 허용한다.
    {
        selector: "variable",
        format: ["camelCase", "UPPER_CASE", "PascalCase"],
        leadingUnderscore: "forbid",
    },
    // 안 쓰는 인자는 `_` 접두사로 표시하는 관용구를 허용한다.
    {
        selector: "parameter",
        format: ["camelCase"],
        leadingUnderscore: "allow",
    },
    // 타입 이름은 PascalCase.
    { selector: "typeLike", format: ["PascalCase"] },
    // 인터페이스에 `I` 접두사를 붙이지 않는다.
    {
        selector: "interface",
        format: ["PascalCase"],
        custom: { regex: "^I[A-Z]", match: false },
    },
    { selector: "enumMember", format: ["PascalCase"] },
    // 함수형 컴포넌트 때문에 PascalCase를 함께 허용한다.
    { selector: "function", format: ["camelCase", "PascalCase"] },
    // import 이름은 우리가 정하는 것이 아니다. React 컴포넌트나 외부 라이브러리는
    // PascalCase가 정상이다.
    { selector: "import", format: ["camelCase", "PascalCase"] },
    // 백엔드 JSON 키는 우리가 정하는 이름이 아니므로 형태를 강제하지 않는다.
    { selector: "objectLiteralProperty", format: null },
    { selector: "typeProperty", format: null },
];

/**
 * ESLint 설정.
 *
 * 코드 정렬은 Prettier가, 규칙 검사는 ESLint가 담당한다. 두 도구가 겹치지 않도록
 * `eslint-config-prettier`를 맨 마지막에 두어 서식 관련 규칙을 전부 끈다.
 *
 * 예외는 없다. 저장소 전체가 이 규칙을 통과해야 한다.
 */
export default tseslint.config(
    {
        ignores: ["dist", "node_modules"],
    },

    // --- TypeScript 소스 ---
    {
        extends: [js.configs.recommended, ...tseslint.configs.recommended],
        files: ["**/*.{ts,tsx}"],
        languageOptions: {
            ecmaVersion: 2020,
            globals: globals.browser,
            parserOptions: {
                // 타입 정보를 쓰는 규칙(naming-convention 등)에 필요하다.
                projectService: true,
                tsconfigRootDir: import.meta.dirname,
            },
        },
        plugins: {
            "react-hooks": reactHooks,
            "react-refresh": reactRefresh,
            jsdoc,
        },
        settings: {
            jsdoc: { mode: "typescript" },
        },
        rules: {
            ...reactHooks.configs.recommended.rules,
            "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],

            "@typescript-eslint/naming-convention": ["error", ...namingSelectors],

            // =====================================================================
            // JSDoc — export되는 public 인터페이스에 요구한다.
            // =====================================================================
            "jsdoc/require-jsdoc": [
                "error",
                {
                    // export된 선언만 검사한다. 모듈 내부 헬퍼는 대상이 아니다.
                    publicOnly: true,
                    require: {
                        FunctionDeclaration: true,
                        ClassDeclaration: true,
                        MethodDefinition: true,
                        ArrowFunctionExpression: true,
                        FunctionExpression: true,
                    },
                    contexts: [
                        "TSInterfaceDeclaration",
                        "TSTypeAliasDeclaration",
                        "TSEnumDeclaration",
                    ],
                    // 빈 껍데기 주석이 자동으로 생기면 오히려 해롭다.
                    enableFixer: false,
                },
            ],
            "jsdoc/require-description": "error",
            "jsdoc/require-param": "error",
            "jsdoc/require-param-description": "error",
            "jsdoc/require-returns": "error",
            "jsdoc/require-returns-description": "error",
            "jsdoc/check-param-names": "error",
            "jsdoc/check-tag-names": "error",
            "jsdoc/check-alignment": "error",
            "jsdoc/empty-tags": "error",
            "jsdoc/no-multi-asterisks": "error",
            // 타입은 시그니처에 이미 있다. JSDoc에 `{string}`처럼 다시 적지 않는다.
            "jsdoc/no-types": "error",
            "jsdoc/require-param-type": "off",
            "jsdoc/require-returns-type": "off",
        },
    },

    // --- 백엔드 API 계약을 그대로 반영하는 계층 ---
    // 요청 본문을 `{ access_token }`처럼 축약 표기로 만들려면 인자 이름이 JSON 키와
    // 같아야 한다. 이 계층에서만 snake_case 인자를 허용한다.
    {
        files: ["src/api.ts", "src/services/**/*.{ts,tsx}"],
        rules: {
            "@typescript-eslint/naming-convention": [
                "error",
                ...namingSelectors.filter((selector) => selector.selector !== "parameter"),
                {
                    selector: "parameter",
                    format: ["camelCase", "snake_case"],
                    leadingUnderscore: "allow",
                },
            ],
        },
    },

    // --- React 컴포넌트 ---
    // .tsx 의 export 는 사실상 전부 컴포넌트이고 반환값은 언제나 렌더링 결과다.
    // @returns 를 요구하면 "렌더링된 컴포넌트"라는 같은 문장만 반복된다.
    // 반환값 설명이 실제로 의미가 있는 .ts(api, services, utils)에는 그대로 적용된다.
    {
        files: ["**/*.tsx"],
        rules: {
            "jsdoc/require-returns": "off",
            "jsdoc/require-returns-description": "off",
        },
    },

    // --- Chakra UI 스니펫 래퍼 ---
    // `chakra-ui/cli snippet add` 로 생성되는 코드다. 우리 로직이 없고 다시
    // 생성하면 덮어써지므로 JSDoc 을 요구하지 않는다. 정렬과 나머지 규칙은
    // 그대로 적용된다.
    {
        files: ["src/components/ui/**/*.{ts,tsx}"],
        rules: {
            "jsdoc/require-jsdoc": "off",
        },
    },

    // --- 설정 파일 ---
    {
        files: ["*.config.{js,ts}", "vite.config.ts"],
        languageOptions: {
            globals: globals.node,
        },
        rules: {
            "jsdoc/require-jsdoc": "off",
        },
    },

    prettier,
);
