import {
  Box,
  Input,
  Portal,
  Spinner,
} from "@chakra-ui/react";
import { Combobox, createListCollection } from "@ark-ui/react/combobox";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { LuChevronDown } from "react-icons/lu";
import { listProjectLanguages } from "../services/projectService";

const EMPTY_LANGUAGES: string[] = [];

interface ProjectLanguageSelectProps {
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  placeholder?: string;
  size?: "sm" | "md" | "lg";
}

export default function ProjectLanguageSelect({
  value,
  onChange,
  disabled = false,
  placeholder = "사용 언어를 선택하세요",
  size = "md",
}: ProjectLanguageSelectProps) {
  const [languageSearch, setLanguageSearch] = useState("");
  const query = useQuery({
    queryKey: ["project-languages"],
    queryFn: listProjectLanguages,
    staleTime: Infinity,
  });
  const languages =
    query.data?.status === "SUCCESS" ? query.data.data : EMPTY_LANGUAGES;

  const collection = useMemo(() => {
    const search = languageSearch.trim().toLocaleLowerCase();
    const selected = new Set(value);
    return createListCollection({
      items: [
        ...value.filter((name) => languages.includes(name)),
        ...languages.filter(
          (name) =>
            !selected.has(name) &&
            (!search || name.toLocaleLowerCase().includes(search))
        ),
      ]
        .map((name) => ({ label: name, value: name })),
    });
  }, [languageSearch, languages, value]);

  const selectLanguageByEnter = () => {
    const search = languageSearch.trim();
    if (!search) return;

    const selected = new Set(value);
    const candidates = collection.items
      .map((item) => item.value)
      .filter((name) => !selected.has(name));
    const exactMatch = candidates.find(
      (name) => name.toLocaleLowerCase() === search.toLocaleLowerCase()
    );
    const nextLanguage = exactMatch ?? candidates[0];
    if (!nextLanguage) return;

    onChange([...value, nextLanguage]);
    setLanguageSearch("");
  };

  return (
    <Combobox.Root
      multiple
      closeOnSelect={false}
      openOnClick
      allowCustomValue={false}
      positioning={{ sameWidth: true }}
      collection={collection}
      value={value}
      inputValue={languageSearch}
      disabled={disabled || query.isLoading}
      onInputValueChange={({ inputValue }) => setLanguageSearch(inputValue)}
      onValueChange={({ value: nextValue }) => {
        onChange(nextValue);
        setLanguageSearch("");
      }}
      onOpenChange={({ open }) => {
        if (!open) setLanguageSearch("");
      }}
    >
      <Box asChild position="relative">
        <Combobox.Control>
          <Input asChild size={size} pr={10}>
            <Combobox.Input
              aria-label="사용 언어 검색 및 선택"
              placeholder={value.length ? value.join(", ") : placeholder}
              onKeyDown={(event) => {
                if (event.key !== "Enter") return;
                event.preventDefault();
                selectLanguageByEnter();
              }}
            />
          </Input>
          <Box
            asChild
            position="absolute"
            top="50%"
            right={2}
            transform="translateY(-50%)"
            display="flex"
            alignItems="center"
            justifyContent="center"
            width={6}
            height={6}
            border={0}
            bg="transparent"
            color="smu.darkGray"
            cursor="pointer"
          >
            <Combobox.Trigger aria-label="사용 언어 목록 열기">
              {query.isLoading ? <Spinner size="xs" /> : <LuChevronDown />}
            </Combobox.Trigger>
          </Box>
        </Combobox.Control>
      </Box>
      <Portal>
        <Combobox.Positioner>
          <Box
            asChild
            zIndex={1500}
            maxH="320px"
            overflowY="auto"
            bg="white"
            borderWidth={1}
            borderColor="smu.gray"
            borderRadius="md"
            shadow="md"
          >
            <Combobox.Content>
              <Combobox.List>
                {collection.items.map((language) => (
                  <Box
                    asChild
                    key={language.value}
                    display="flex"
                    alignItems="center"
                    justifyContent="space-between"
                    px={3}
                    py={2}
                    fontSize="sm"
                    cursor="pointer"
                    _highlighted={{ bg: "#edf3fb" }}
                  >
                    <Combobox.Item item={language}>
                      <Combobox.ItemText>
                        {language.label}
                      </Combobox.ItemText>
                      <Combobox.ItemIndicator>✓</Combobox.ItemIndicator>
                    </Combobox.Item>
                  </Box>
                ))}
                {collection.items.length === 0 && (
                  <Box px={3} py={2} color="smu.darkGray" fontSize="sm">
                    검색 결과가 없습니다.
                  </Box>
                )}
              </Combobox.List>
            </Combobox.Content>
          </Box>
        </Combobox.Positioner>
      </Portal>
    </Combobox.Root>
  );
}
